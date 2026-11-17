import { json } from "react-router-dom";
import { toast } from "react-toastify";
import { createHttpErrorToastBudget } from "./httpErrorToastBudget";
import { createCsrfTransport, csrfFailureKind, isUnsafeMethod } from "./csrfTransport.mjs";
import i18n from "@/i18n";

// Vite does not define the legacy CRA environment variable in fake mode.
// Keep legacy loader calls rooted at the local Mirage API instead of creating
// URLs such as "undefinedget_player_profile".
const configuredApi = process.env.REACT_APP_API_URL;
const CRCON_API =
  configuredApi && configuredApi !== "undefined" ? configuredApi : "/";
const SESSION_EXPIRY_EVENT = "crcon:session-expired";
const SESSION_RECOVERY_COMMANDS = new Set(["login", "logout"]);

let sessionExpired = false;
const HTTP_ERROR_TOAST_SUMMARY_ID = "crcon:http-error-summary";
const httpErrorToastBudget = createHttpErrorToastBudget();

// Intended for a diagnostics page/support bundle.  Return copies so callers
// cannot mutate the bounded, privacy-safe in-memory history.
export const getRecentHttpErrorDiagnostics = () =>
  httpErrorToastBudget.diagnostics();

const showBoundedHttpErrorToast = ({ signature, message, level = "error" }) => {
  const result = httpErrorToastBudget.record(signature);
  const toastId = `crcon:http-error:${signature}`;
  const toastMethod = level === "warn" ? toast.warn : toast.error;
  const toastType = level === "warn" ? "warning" : "error";
  if (result.kind === "repeat") {
    if (toast.isActive(toastId)) {
      toast.update(toastId, {
        render: i18n.t("sharedOperations.http.repeatedError", {
          message,
          count: result.count,
        }),
        type: toastType,
      });
    }
    return;
  }

  if (result.kind === "new") {
    toastMethod(message, { toastId });
    return;
  }

  const summary = i18n.t("sharedOperations.http.suppressedErrors", {
    count: result.suppressed,
  });
  if (toast.isActive(HTTP_ERROR_TOAST_SUMMARY_ID)) {
    toast.update(HTTP_ERROR_TOAST_SUMMARY_ID, {
      render: summary,
      type: "warning",
    });
  } else {
    toast.warn(summary, { toastId: HTTP_ERROR_TOAST_SUMMARY_ID });
  }
};

const isSessionRecoveryCommand = (command) =>
  SESSION_RECOVERY_COMMANDS.has(String(command ?? "").replace(/^\//, ""));

export const isSessionExpired = () => sessionExpired;

export const clearExpiredSession = () => {
  sessionExpired = false;
};

const markSessionExpired = (command) => {
  if (sessionExpired || isSessionRecoveryCommand(command)) return;

  sessionExpired = true;
  csrfTransport?.reset();
  if (typeof window !== "undefined") {
    // Let the mounted auth boundary subscribe before the first fast API
    // response from a local/fake backend asks it to redirect.
    window.setTimeout(
      () => window.dispatchEvent(new CustomEvent(SESSION_EXPIRY_EVENT)),
      0
    );
  }
};

export { SESSION_EXPIRY_EVENT };

let csrfTransport;
export async function fetchWithCsrf(input, options = {}) {
  csrfTransport ??= createCsrfTransport({
    apiBase: CRCON_API,
    pageOrigin: document.location.origin,
    readCookie: () => document.cookie,
    fetcher: (...args) => fetch(...args),
  });
  try {
    const response = await csrfTransport.fetchWithCsrf(input, options);
    const failure = csrfFailureKind(response);
    if (failure) throw new CsrfError(failure);
    return response;
  } catch (error) {
    if (error.name === "CsrfTransportError") {
      throw new CsrfError(error.code);
    }
    throw error;
  }
}

async function requestFactory({
  method = "GET",
  cmd,
  params = {}, // For query parameters (GET)
  payload = {}, // For body data (POST)
  throwRouteError = true,
  signal,
  headers = { "Content-Type": "application/json" },
} = {}) {
  if (sessionExpired && !isSessionRecoveryCommand(cmd)) {
    throw new AuthError(i18n.t("sharedOperations.http.sessionExpired"), cmd);
  }

  // Construct the full URL using the URL API
  const base = new URL(CRCON_API, document.location.origin);
  const url = new URL(cmd, base);

  // Append query parameters for GET requests
  if (params instanceof URLSearchParams) {
    url.search = params.toString();
  } else if (method === "GET" && Object.keys(params).length > 0) {
    url.search = new URLSearchParams(params).toString();
  }

  // Define request options shared by the original request and a possible
  // CSRF-only recovery retry.
  const requestOptions = {
    signal,
    method,
    mode: "cors",
    cache: "default",
    credentials: "include",
    headers,
    redirect: "follow",
    referrerPolicy: "origin",
  };

  // Add a body for all mutating JSON requests.
  if (isUnsafeMethod(method)) {
    const contentType = new Headers(headers).get("Content-Type");
    requestOptions.body =
      contentType === "application/json" ? JSON.stringify(payload) : payload;
  }

  const req = { method: String(method).toUpperCase() };
  try {
    const res = await fetchWithCsrf(url.toString(), requestOptions);
    return await handleFetchResponse(req, res, cmd);
  } catch (error) {
    if (signal?.aborted) throw error;
    if (throwRouteError) {
      const message =
        error?.message || error?.text || i18n.t("sharedOperations.http.requestFailed");
      const status =
        Number.isInteger(error?.status) &&
        error.status >= 400 &&
        error.status <= 599
          ? error.status
          : 500;

      // Response.statusText only accepts HTTP reason-phrase characters. CRCON
      // errors may contain translated text, player names or map names (for
      // example "Huế") and therefore must remain in the JSON body instead.
      throw json(
        { message },
        {
          status,
          statusText: "Request failed",
        }
      );
    }
    throw error;
  }
}

async function handleFetchResponse(req, res, cmd) {
  let data, error;

  const contentType = res.headers.get("content-type");
  const isJSON = contentType && contentType.includes("application/json");
  const isText = contentType && contentType.includes("text/");
  const isHTML = contentType && contentType.includes("text/html");

  // A missing Vite/Mirage API route may fall through to the SPA document with
  // HTTP 200. Never let that HTML become a seemingly valid form value.
  if (isHTML) {
    throw new NotJSONResponseError(
      i18n.t("sharedOperations.http.htmlResponse", { command: cmd })
    );
  }

  if (isJSON) {
    data = await parseJsonResponse(res);
    error = data.error;
    if (req.method === "GET") {
      data = data.result;
    }
  } else if (isText) {
    data = await res.text();
  }

  if (!res.ok) {
    if (isText) {
      error = data;
    }
    if (res.status === 503 && cmd === "get_public_info" && error === "game_server_unavailable") {
      throw new APIError(i18n.t("sharedOperations.http.gameServerUnavailable"), cmd, 503);
    }
    switch (res.status) {
      case 401:
        markSessionExpired(cmd);
        throw new AuthError(i18n.t("sharedOperations.http.notAuthenticated"), cmd);
      case 403:
        throw new PermissionError(i18n.t("sharedOperations.http.notAuthorized"), cmd);
      case 504:
        throw new CRCONServerDownError(
          i18n.t("sharedOperations.http.connectionProblem")
        );
      default:
        throw new APIError(error, cmd, res.status);
    }
  }

  if (cmd === "login") {
    clearExpiredSession();
  }
  return data;
}

async function parseJsonResponse(response) {
  try {
    return await response.json();
  } catch {
    throw new NotJSONResponseError(i18n.t("sharedOperations.http.invalidJson"));
  }
}

export const cmd = {
  GET_API_DOCUMENTATION: (params) =>
    requestFactory({ method: "GET", cmd: "get_api_documentation", ...params }),
  GET_UPDATE_CHANNEL: (params) =>
    requestFactory({ method: "GET", cmd: "get_update_channel", ...params }),
  SET_OWN_RELEASE_HIGHLIGHT_STATE: (payload) =>
    requestFactory({ method: "POST", cmd: "set_own_release_highlight_state", payload, throwRouteError: false }),
  APPLY_QUEUE_LENGTH: (params) =>
    requestFactory({ method: "POST", cmd: "apply_queue_length", ...params }),
  APPLY_VIP_SLOTS_NUM: (params) =>
    requestFactory({ method: "POST", cmd: "apply_vip_slots_num", ...params }),
  ADD_CONSOLE_ADMIN: (params) =>
    requestFactory({ method: "POST", cmd: "add_admin", ...params }),
  ADD_MAP_TO_VOTEMAP: (params) =>
    requestFactory({ method: "POST", cmd: "add_map_to_votemap", ...params }),
  ADD_MESSAGE_TEMPLATE: (params) =>
    requestFactory({ method: "POST", cmd: "add_message_template", ...params }),
  ADD_VIP: (params) =>
    requestFactory({ method: "POST", cmd: "add_vip", ...params }),
  AUTHENTICATE: (params) =>
    requestFactory({ method: "POST", cmd: "login", ...params }),
  MESSAGE_PLAYER: (params) =>
    requestFactory({ method: "POST", cmd: "message_player", ...params }),
  TEST_PLAYER_CAMPAIGN: (params) =>
    requestFactory({ method: "POST", cmd: "test_player_campaign", ...params }),
  TEST_VIP_LIFECYCLE_MESSAGE: (params) =>
    requestFactory({
      method: "POST",
      cmd: "test_vip_lifecycle_message",
      ...params,
    }),
  MESSAGE_ALL_PLAYERS: (params) =>
    requestFactory({ method: "POST", cmd: "message_all_players", ...params }),
  BULK_MESSAGE_PLAYERS: (params) =>
    requestFactory({ method: "POST", cmd: "bulk_message_players", ...params }),
  CLEAR_APPLICATION_CACHE: (params) =>
    requestFactory({ method: "POST", cmd: "clear_cache", ...params }),
  DELETE_CONSOLE_ADMIN: (params) =>
    requestFactory({ method: "POST", cmd: "remove_admin", ...params }),
  DELETE_MESSAGE_TEMPLATE: (params) =>
    requestFactory({
      method: "POST",
      cmd: "delete_message_template",
      ...params,
    }),
  DELETE_VIP: (params) =>
    requestFactory({ method: "POST", cmd: "remove_vip", ...params }),
  DISBAND_SQUAD: (params) =>
    requestFactory({ method: "POST", cmd: "disband_squad_by_name", ...params }),
  EDIT_MESSAGE_TEMPLATE: (params) =>
    requestFactory({ method: "POST", cmd: "edit_message_template", ...params }),
  EDIT_PLAYER_ACCOUNT: (params) =>
    requestFactory({ method: "POST", cmd: "edit_player_account", ...params }),
  EDIT_PLAYER_SOLDIER: (params) =>
    requestFactory({ method: "POST", cmd: "edit_player_soldier", ...params }),
  FLAG_PLAYER: (params) =>
    requestFactory({ method: "POST", cmd: "flag_player", ...params }),
  GET_AUDIT_LOGS: (params) =>
    requestFactory({ method: "GET", cmd: "get_audit_logs", ...params }),
  GET_AUDIT_LOGS_AUTOCOMPLETE: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_audit_logs_autocomplete",
      ...params,
    }),
  GET_ALL_MESSAGE_TEMPLATES: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_all_message_templates",
      ...params,
    }),
  GET_AUTOSETTINGS: (params) =>
    requestFactory({ method: "GET", cmd: "get_auto_settings", ...params }),
  PREVIEW_AUTOSETTINGS: (params) =>
    requestFactory({
      method: "POST",
      cmd: "preview_auto_settings",
      ...params,
    }),
  GET_AUTOBALANCER_STATUS: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_autobalancer_status",
      ...params,
    }),
  GET_AUTOBALANCER_CONFIG: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_autobalancer_config",
      ...params,
    }),
  GET_AUTOBALANCER_SHADOW_OVERVIEW: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_autobalancer_shadow_overview",
      ...params,
    }),
  GET_AUTOBALANCER_ROUND_ARCHIVE: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_autobalancer_round_archive",
      ...params,
    }),
  GET_AUTOBALANCER_HISTORY_DASHBOARD: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_autobalancer_history_dashboard",
      ...params,
    }),
  GET_BANS: (params) =>
    requestFactory({ method: "GET", cmd: "get_bans", ...params }),
  GET_BLACKLISTS: (params) =>
    requestFactory({ method: "GET", cmd: "get_blacklists", ...params }),
  GET_BROADCAST_CONFIG: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_auto_broadcasts_config",
      ...params,
    }),
  GET_CAMPAIGN_DELIVERY_STATUS: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_campaign_delivery_status",
      ...params,
    }),
  GET_VIP_LIFECYCLE_STATUS: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_vip_lifecycle_status",
      ...params,
    }),
  PREVIEW_VIP_LIFECYCLE: (params) =>
    requestFactory({
      method: "GET",
      cmd: "preview_vip_lifecycle",
      ...params,
    }),
  GET_BROADCAST_MESSAGE: (params) =>
    requestFactory({ method: "GET", cmd: "get_broadcast_message", ...params }),
  GET_CAMERA_NOTIFICATION_CONFIG: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_camera_notification_config",
      ...params,
    }),
  GET_COMPLETED_GAME_DETAIL: (params) =>
    requestFactory({ method: "GET", cmd: "get_map_scoreboard", ...params }),
  GET_COMPLETED_GAMES: (params) =>
    requestFactory({ method: "GET", cmd: "get_scoreboard_maps", ...params }),
  GET_CONSOLE_ADMIN_GROUPS: (params) =>
    requestFactory({ method: "GET", cmd: "get_admin_groups", ...params }),
  GET_CONSOLE_ADMINS: (params) =>
    requestFactory({ method: "GET", cmd: "get_admin_ids", ...params }),
  GET_CRCON_MODS: (params) =>
    requestFactory({ method: "GET", cmd: "get_online_mods", ...params }),
  GET_CRCON_SERVER_CONNECTION: (params) =>
    requestFactory({ method: "GET", cmd: "get_connection_info", ...params }),
  GET_GAME_MODE: (params) =>
    requestFactory({ method: "GET", cmd: "get_game_mode", ...params }),
  GET_GAME_SERVER_LIST: (params) =>
    requestFactory({ method: "GET", cmd: "get_server_list", ...params }),
  GET_GAME_SERVER_STATUS: (params) =>
    requestFactory({ method: "GET", cmd: "get_status", ...params }),
  GET_GAME_STATE: (params) =>
    requestFactory({ method: "GET", cmd: "get_gamestate", ...params }),
  // Yes, it is POST request, but it is not a POST command => it's not mutating the server state
  GET_HISTORICAL_LOGS: (params) =>
    requestFactory({ method: "POST", cmd: "get_historical_logs", ...params }),
  GET_INGAME_MODS: (params) =>
    requestFactory({ method: "GET", cmd: "get_ingame_mods", ...params }),
  GET_LIVE_GAME: (params) =>
    requestFactory({ method: "GET", cmd: "get_live_game_stats", ...params }),
  // Yes, it is POST request, but it is not a POST command => it's not mutating the server state
  GET_LIVE_LOGS: (params) =>
    requestFactory({ method: "POST", cmd: "get_recent_logs", ...params }),
  GET_DASHBOARD_LOGS: (params) =>
    requestFactory({
      method: "POST",
      cmd: "get_recent_logs_summary",
      ...params,
    }),
  GET_LIVE_SESSIONS: (params) =>
    requestFactory({ method: "GET", cmd: "get_live_scoreboard", ...params }),
  GET_LIVE_TEAMS: ({ params = {}, ...options } = {}) =>
    requestFactory({
      method: "GET",
      cmd: "get_team_view",
      ...options,
      params: { ...params, compact: "true" },
    }),
  GET_CURRENT_MAP: (params) =>
    requestFactory({ method: "GET", cmd: "get_map", ...params }),
  GET_MAPS: (params) =>
    requestFactory({ method: "GET", cmd: "get_maps", ...params }),
  GET_MAP_ROTATION: (params) =>
    requestFactory({ method: "GET", cmd: "get_map_rotation", ...params }),
  GET_MAP_SEQUENCE: (params) =>
    requestFactory({ method: "GET", cmd: "get_map_sequence", ...params }),
  GET_MAP_OBJECTIVES: (params) =>
    requestFactory({ method: "GET", cmd: "get_objective_rows", ...params }),
  GET_MAP_ROTATION_SHUFFLE: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_map_shuffle_enabled",
      ...params,
    }),
  GET_MESSAGE_TEMPLATE: (params) =>
    requestFactory({ method: "GET", cmd: "get_message_template", ...params }),
  GET_MESSAGE_TEMPLATES: (params) =>
    requestFactory({ method: "GET", cmd: "get_message_templates", ...params }),
  GET_SEEDING_CONFIG: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_auto_mod_seeding_config",
      ...params,
    }),
  GET_NO_LEADER_CONFIG: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_auto_mod_no_leader_config",
      ...params,
    }),
  GET_NO_SOLO_TANK_CONFIG: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_auto_mod_solo_tank_config",
      ...params,
    }),
  GET_LEVEL_CONFIG: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_auto_mod_level_config",
      ...params,
    }),
  GET_NAME_KICKS_CONFIG: (params) =>
    requestFactory({ method: "GET", cmd: "get_name_kick_config", ...params }),
  GET_VAC_CONFIG: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_vac_game_bans_config",
      ...params,
    }),
  GET_SEEDING_REWARD_CONFIG: (params) =>
    requestFactory({ method: "GET", cmd: "get_seed_vip_config", ...params }),
  GET_CHAT_COMMANDS_CONFIG: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_chat_commands_config",
      ...params,
    }),
  GET_RCON_CHAT_COMMANDS_CONFIG: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_rcon_chat_commands_config",
      ...params,
    }),
  GET_ONLINE_PLAYERS: (params) =>
    requestFactory({ method: "GET", cmd: "get_players", ...params }),
  GET_MOBILE_INCIDENTS: (params) =>
    requestFactory({
      method: "GET",
      cmd: "/api/mobile/v1/incidents",
      ...params,
    }),
  UPDATE_MOBILE_INCIDENT: ({ incidentId, payload, ...params }) =>
    requestFactory({
      method: "PATCH",
      cmd: `/api/mobile/v1/incidents/${incidentId}`,
      payload,
      ...params,
    }),
  GET_PERMISSIONS: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_own_user_permissions",
      ...params,
    }),
  GET_OWN_APPEARANCE: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_own_user_appearance",
      ...params,
    }),
  GET_OWN_LIVE_VIEW: () =>
    requestFactory({ method: "GET", cmd: "get_own_user_live_view" }),
  SET_OWN_LIVE_VIEW: (payload) =>
    requestFactory({ method: "PUT", cmd: "set_own_user_live_view", payload }),
  SET_OWN_APPEARANCE: (payload, params = {}) =>
    requestFactory({
      method: "PUT",
      cmd: "set_own_user_appearance",
      payload,
      ...params,
    }),
  GET_PLAYER: (params) =>
    requestFactory({ method: "GET", cmd: "get_player_profile", ...params }),
  GET_PLAYER_BANS: (params) =>
    requestFactory({ method: "GET", cmd: "get_ban", ...params }),
  GET_PLAYER_COMMENTS: (params) =>
    requestFactory({ method: "GET", cmd: "get_player_comments", ...params }),
  GET_PLAYER_MESSAGES: (params) =>
    requestFactory({ method: "GET", cmd: "get_player_messages", ...params }),
  // Yes, it is POST request, but it is not a POST command => it's not mutating the server state
  GET_PLAYERS_RECORDS: (params) =>
    requestFactory({ method: "POST", cmd: "get_players_history", ...params }),
  GET_PROFANITIES: (params) =>
    requestFactory({ method: "GET", cmd: "get_profanities", ...params }),
  GET_PUBLIC_GAME_STATE: (params) =>
    requestFactory({ method: "GET", cmd: "get_public_info", ...params }),
  GET_REAL_VIP_CONFIG: (params) =>
    requestFactory({ method: "GET", cmd: "get_real_vip_config", ...params }),
  GET_SERVER_NAME: (params) =>
    requestFactory({ method: "GET", cmd: "get_name", ...params }),
  GET_SERVER_NAME_CHANGE_CONFIG: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_server_name_change_config",
      ...params,
    }),
  GET_SERVER_SETTINGS: (params) =>
    requestFactory({ method: "GET", cmd: "get_server_settings", ...params }),
  GET_GENERAL_SETTING_EFFECTS: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_general_setting_effects",
      ...params,
    }),
  GET_SERVICES: (params) =>
    requestFactory({ method: "GET", cmd: "get_services", ...params }),
  GET_OPERATIONAL_HEALTH: (params) =>
    requestFactory({ method: "GET", cmd: "get_operational_health", ...params }),
  GET_SUPPORT_DIAGNOSTICS_PREVIEW: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_support_diagnostics_preview",
      ...params,
    }),
  GET_WEBHOOK_DEAD_LETTERS: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_webhook_dead_letters",
      ...params,
    }),
  RETRY_WEBHOOK_DEAD_LETTER: (params) =>
    requestFactory({
      method: "POST",
      cmd: "retry_webhook_dead_letter",
      ...params,
    }),
  GET_SYSTEM_USAGE: (params) =>
    requestFactory({ method: "GET", cmd: "get_system_usage", ...params }),
  GET_VERSION: (params) =>
    requestFactory({ method: "GET", cmd: "get_version", ...params }),
  GET_VIPS: (params) =>
    requestFactory({ method: "GET", cmd: "get_vip_ids", ...params }),
  GET_VOTEKICK_AUTOTOGGLE_CONFIG: (params) =>
    requestFactory({
      method: "GET",
      cmd: "get_votekick_autotoggle_config",
      ...params,
    }),
  GET_VOTEMAP_WHITELIST: (params) =>
    requestFactory({ method: "GET", cmd: "get_votemap_whitelist", ...params }),
  GET_VOTEMAP_CONFIG: (params) =>
    requestFactory({ method: "GET", cmd: "get_votemap_config", ...params }),
  GET_VOTEMAP_STATUS: (params) =>
    requestFactory({ method: "GET", cmd: "get_votemap_status", ...params }),
  GET_VOTEMAP_RESULTS: (params) =>
    requestFactory({ method: "GET", cmd: "get_votemap_results", ...params }),
  GET_WELCOME_MESSAGE: (params) =>
    requestFactory({ method: "GET", cmd: "get_welcome_message", ...params }),
  IS_AUTHENTICATED: (params) =>
    requestFactory({ method: "GET", cmd: "is_logged_in", ...params }),
  LOGOUT: (params) =>
    requestFactory({ method: "GET", cmd: "logout", ...params }),
  RECONNECT_GAME_SERVER: (params) =>
    requestFactory({ method: "POST", cmd: "reconnect_gameserver", ...params }),
  REMOVE_MATCH_TIMER: (params) =>
    requestFactory({ method: "POST", cmd: "remove_match_timer", ...params }),
  REMOVE_PLAYER_FROM_SQUAD: (params) =>
    requestFactory({
      method: "POST",
      cmd: "remove_player_from_squad",
      ...params,
    }),
  REMOVE_WARMUP_TIMER: (params) =>
    requestFactory({ method: "POST", cmd: "remove_warmup_timer", ...params }),
  REMOVE_MAP_FROM_VOTEMAP: (params) =>
    requestFactory({
      method: "POST",
      cmd: "remove_map_from_votemap",
      ...params,
    }),
  RESET_VOTEMAP_STATE: (params) =>
    requestFactory({ method: "POST", cmd: "reset_votemap_state", ...params }),
  RESET_VOTEMAP_WHITELIST: (params) =>
    requestFactory({
      method: "POST",
      cmd: "reset_map_votemap_whitelist",
      ...params,
    }),
  RESET_VOTEKICK_THRESHOLDS: (params) =>
    requestFactory({
      method: "POST",
      cmd: "reset_votekick_thresholds",
      ...params,
    }),
  SEND_VOTEMAP_REMINDER: (params) =>
    requestFactory({ method: "POST", cmd: "send_votemap_reminder", ...params }),
  APPROVE_AUTOBALANCER: (params) =>
    requestFactory({
      method: "POST",
      cmd: "approve_autobalancer_proposal",
      ...params,
    }),
  CANCEL_AUTOBALANCER: (params) =>
    requestFactory({
      method: "POST",
      cmd: "cancel_autobalancer_incident",
      ...params,
    }),
  REVIEW_AUTOBALANCER_SHADOW_DECISION: (params) =>
    requestFactory({
      method: "POST",
      cmd: "review_autobalancer_shadow_decision",
      ...params,
    }),
  SET_AUTOBALANCE_ENABLED: (params) =>
    requestFactory({
      method: "POST",
      cmd: "set_autobalance_enabled",
      ...params,
    }),
  SET_AUTOBALANCE_THRESHOLD: (params) =>
    requestFactory({
      method: "POST",
      cmd: "set_autobalance_threshold",
      ...params,
    }),
  SET_AUTOSETTINGS: (params) =>
    requestFactory({ method: "POST", cmd: "set_auto_settings", ...params }),
  SET_BROADCAST_CONFIG: (params) =>
    requestFactory({
      method: "POST",
      cmd: "set_auto_broadcasts_config",
      ...params,
    }),
  SET_BROADCAST_MESSAGE: (params) =>
    requestFactory({ method: "POST", cmd: "set_broadcast", ...params }),
  SET_CAMERA_NOTIFICATION_CONFIG: (params) =>
    requestFactory({
      method: "POST",
      cmd: "set_camera_notification_config",
      ...params,
    }),
  SET_DYNAMIC_WEATHER_ENABLED: (params) =>
    requestFactory({
      method: "POST",
      cmd: "set_dynamic_weather_enabled",
      ...params,
    }),
  SET_IDLE_AUTOKICK_TIME: (params) =>
    requestFactory({
      method: "POST",
      cmd: "set_idle_autokick_time",
      ...params,
    }),
  SET_MAP: (params) =>
    requestFactory({ method: "POST", cmd: "set_map", ...params }),
  SET_MAP_OBJECTIVES: (params) =>
    requestFactory({ method: "POST", cmd: "set_game_layout", ...params }),
  SET_MAP_ROTATION: (params) =>
    requestFactory({ method: "POST", cmd: "set_map_rotation", ...params }),
  SET_MAP_SEQUENCE: (params) =>
    requestFactory({ method: "POST", cmd: "set_map_sequence", ...params }),
  SET_MAP_ROTATION_SHUFFLE: (params) =>
    requestFactory({
      method: "POST",
      cmd: "set_map_shuffle_enabled",
      ...params,
    }),
  SET_MATCH_TIMER: (params) =>
    requestFactory({ method: "POST", cmd: "set_match_timer", ...params }),
  SET_MAX_PING_AUTOKICK: (params) =>
    requestFactory({ method: "POST", cmd: "set_max_ping_autokick", ...params }),
  SET_PROFANITIES: (params) =>
    requestFactory({ method: "POST", cmd: "set_profanities", ...params }),
  SET_QUEUE_LENGTH: (params) =>
    requestFactory({ method: "POST", cmd: "set_queue_length", ...params }),
  SET_REAL_VIP_CONFIG: (params) =>
    requestFactory({ method: "POST", cmd: "set_real_vip_config", ...params }),
  SET_SERVER_NAME: (params) =>
    requestFactory({ method: "POST", cmd: "set_server_name", ...params }),
  SET_SERVER_NAME_CHANGE_CONFIG: (params) =>
    requestFactory({
      method: "POST",
      cmd: "set_server_name_change_config",
      ...params,
    }),
  SET_TEAM_SWITCH_COOLDOWN: (params) =>
    requestFactory({
      method: "POST",
      cmd: "set_team_switch_cooldown",
      ...params,
    }),
  SET_VIP_SLOTS_NUM: (params) =>
    requestFactory({ method: "POST", cmd: "set_vip_slots_num", ...params }),
  SET_VOTEKICK_AUTOTOGGLE_CONFIG: (params) =>
    requestFactory({
      method: "POST",
      cmd: "set_votekick_autotoggle_config",
      ...params,
    }),
  SET_VOTEKICK_ENABLED: (params) =>
    requestFactory({ method: "POST", cmd: "set_votekick_enabled", ...params }),
  SET_VOTEKICK_THRESHOLDS: (params) =>
    requestFactory({
      method: "POST",
      cmd: "set_votekick_thresholds",
      ...params,
    }),
  SET_VOTEMAP_CONFIG: (params) =>
    requestFactory({ method: "POST", cmd: "set_votemap_config", ...params }),
  SET_VOTEMAP_WINNER: (params) =>
    requestFactory({ method: "POST", cmd: "set_votemap_winner", ...params }),
  SET_VOTEMAP_WHITELIST: (params) =>
    requestFactory({ method: "POST", cmd: "set_votemap_whitelist", ...params }),
  SET_WARMUP_TIMER: (params) =>
    requestFactory({ method: "POST", cmd: "set_warmup_timer", ...params }),
  SET_WELCOME_MESSAGE: (params) =>
    requestFactory({ method: "POST", cmd: "set_welcome_message", ...params }),
  TOGGLE_SERVICE: (params) =>
    requestFactory({ method: "POST", cmd: "do_service", ...params }),
  UNFLAG_PLAYER: (params) =>
    requestFactory({ method: "POST", cmd: "unflag_player", ...params }),
  // Files
  DOWNLOAD_VIP_FILE: (params) =>
    requestFactory({ method: "GET", cmd: "download_vips", ...params }),
  UPLOAD_VIP_FILE: (params) =>
    requestFactory({ method: "POST", cmd: "upload_vips", ...params }),
  GET_UPLOAD_VIP_FILE_RESPONSE: (params) =>
    requestFactory({ method: "GET", cmd: "upload_vips_result", ...params }),
};

export async function mobileRequest(path, { method = "GET", payload } = {}) {
  const apiBase = new URL(CRCON_API, document.location.origin);
  const url = new URL(`mobile/v1/${path}`, apiBase);
  const response = await fetchWithCsrf(url, {
    method,
    mode: "cors",
    cache: "no-store",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    redirect: "follow",
    referrerPolicy: "origin",
    ...(method !== "GET" && method !== "HEAD"
      ? { body: JSON.stringify(payload ?? {}) }
      : {}),
  });
  const envelope = await parseJsonResponse(response);
  if (!response.ok || envelope.failed) {
    throw new APIError(
      envelope.error || i18n.t("sharedOperations.http.mobileRequestFailed"),
      path,
      response.status
    );
  }
  return envelope.result;
}

export async function discordRequest(path, { method = "GET", payload } = {}) {
  const apiBase = new URL(CRCON_API, document.location.origin);
  const url = new URL(`discord/v1/${path}`, apiBase);
  const response = await fetchWithCsrf(url, {
    method,
    mode: "cors",
    cache: "no-store",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    redirect: "follow",
    referrerPolicy: "origin",
    ...(method !== "GET" && method !== "HEAD"
      ? { body: JSON.stringify(payload ?? {}) }
      : {}),
  });
  const envelope = await parseJsonResponse(response);
  if (!response.ok || envelope.failed) {
    throw new APIError(
      envelope.error || i18n.t("sharedOperations.http.discordRequestFailed"),
      path,
      response.status
    );
  }
  return envelope.result;
}

export function execute(command, data) {
  return postData(CRCON_API + command, data);
}

// used for React Router loaders
export function handleHttpError(error) {
  let errorObject, init;

  switch (error.name) {
    case "CsrfError":
      errorObject = { message: error.message, error: error.name };
      init = { status: 403 };
      break;
    case "PermissionError":
      errorObject = {
        message: i18n.t("sharedOperations.http.notAuthorized"),
        error: error?.name,
        command: error?.command,
      };
      init = { status: 403 };
      break;
    case "AuthError":
      errorObject = {
        message: i18n.t("sharedOperations.http.notAuthenticated"),
        error: error?.name,
        command: error?.command,
      };
      init = { status: 401 };
      break;
    case "HLLCommandFailedError":
      errorObject = {
        message: error?.message,
        error: error?.name,
        command: error?.command,
      };
      init = { status: 404 };
      break;
    case "CRCONServerDownError":
      errorObject = {
        message: error?.message,
        error: error?.name,
        command: error?.command,
      };
      init = { status: 504 };
      break;
    default:
      errorObject = {
        message: error?.message ?? i18n.t("sharedOperations.http.unexpectedError"),
        error: error?.name,
        command: error?.command,
      };
      init = { status: 400 };
      break;
  }

  throw json(errorObject, init);
}

class CsrfError extends Error {
  constructor(kind) {
    const key = kind === "request" ? "csrfRequestRejected" : "csrfSessionChanged";
    super(i18n.t(`sharedOperations.http.${key}`));
    this.name = "CsrfError";
    this.status = 403;
    this.text = this.message;
  }
}

class AuthError extends Error {
  constructor(message, command) {
    super(message ?? i18n.t("sharedOperations.http.notAuthenticated"));
    this.name = "AuthError";
    this.status = 401;
    this.text = message;
    this.command = command;
  }
}

class PermissionError extends Error {
  constructor(message, command) {
    super(message ?? i18n.t("sharedOperations.http.notAuthorized"));
    this.command = command;
    this.name = "PermissionError";
    this.status = 403;
    this.text = message;
  }
}

class HLLCommandFailedError extends Error {
  constructor(message, command) {
    super(message);
    this.command = command;
    this.name = "HLLCommandFailedError";
    this.text = message;
    this.status = 404;
  }
}

class ConnectionError extends Error {
  constructor(message) {
    super(message);
    this.name = "ConnectionError";
    this.status = 504;
    this.text = message;
  }
}

class CRCONServerDownError extends Error {
  constructor(message) {
    super(message);
    this.name = "CRCONServerDownError";
    this.status = 504;
    this.text = message;
  }
}

class NotJSONResponseError extends Error {
  constructor(message) {
    super(message);
    this.name = "NotJSONResponseError";
    this.status = 500;
    this.text = message;
  }
}

class APIError extends Error {
  constructor(message, command, status) {
    super(message);
    this.command = command;
    this.name = "APIError";
    this.status = status ?? 400;
    this.text = message;
  }
}

async function handle_response_status(response) {
  if (response.status === 401) {
    throw new AuthError(i18n.t("sharedOperations.http.signInRequired"));
  }

  if (response.status === 403) {
    throw new PermissionError(
      i18n.t("sharedOperations.http.notAuthorized"),
      response.url.slice(response.url.indexOf("/api/") + "/api/".length)
    );
  }

  if (response.status === 504) {
    throw new CRCONServerDownError(
      `${response.statusText}. ${i18n.t("sharedOperations.http.serverNotResponding")}`
    );
  }

  return response;
}

async function handle_http_errors(error) {
  const name = String(error?.name ?? "UnknownError");
  const status = Number.isFinite(error?.status) ? error.status : "none";
  const command = String(error?.command ?? "none").replace(
    /[^a-zA-Z0-9_/-]/g,
    ""
  );

  if (name === "CsrfError") {
    showBoundedHttpErrorToast({
      signature: "csrf",
      message: error.message,
      level: "warn",
    });
  } else if (name === "AuthError") {
    showBoundedHttpErrorToast({
      signature: "auth",
      message: i18n.t("sharedOperations.http.signInRequired"),
      level: "warn",
    });
  } else if (name === "PermissionError") {
    showBoundedHttpErrorToast({
      signature: `permission:${command || "unknown"}`,
      message: i18n.t("sharedOperations.http.actionNotAllowed", {
        command: command || i18n.t("sharedOperations.http.thisAction"),
      }),
      level: "warn",
    });
  } else if (name === "InvalidLogin") {
    showBoundedHttpErrorToast({
      signature: "invalid-login",
      message: i18n.t("sharedOperations.http.invalidLogin"),
      level: "warn",
    });
  } else if (name === "TypeError" || name === "SyntaxError") {
    showBoundedHttpErrorToast({
      signature: "api-unreachable",
      message:
        i18n.t("sharedOperations.http.apiUnreachable"),
    });
  } else {
    showBoundedHttpErrorToast({
      signature: `${name}:${status}:${command || "none"}`,
      message:
        i18n.t("sharedOperations.http.diagnosticsHint"),
    });
  }
}

async function get(path) {
  const response = await fetchWithCsrf(`${CRCON_API}${path}`, {
    method: "GET", // *GET, POST, PUT, DELETE, etc.
    mode: "cors", // no-cors, *cors, same-origin
    cache: "default", // *default, no-cache, reload, force-cache, only-if-cached
    credentials: "include", // include, *same-origin, omit
    redirect: "follow", // manual, *follow, error
    referrerPolicy: "origin", // no-referrer, *client
  });

  return handle_response_status(response);
}

async function postData(url = "", data = {}) {
  // Default options are marked with *
  const response = await fetchWithCsrf(url, {
    method: "POST", // *GET, POST, PUT, DELETE, etc.
    mode: "cors", // no-cors, *cors, same-origin
    cache: "default", // *default, no-cache, reload, force-cache, only-if-cached
    credentials: "include", // include, *same-origin, omit
    headers: {
      "Content-Type": "application/json",
    },
    redirect: "follow", // manual, *follow, error
    referrerPolicy: "origin", // no-referrer, *client
    body: JSON.stringify(data), // body data type must match "Content-Type" header
  });

  return handle_response_status(response); // parses JSON response into native JavaScript objects
}

async function showResponse(response, command, showSuccess) {
  if (!response.ok) {
    toast.error(i18n.t("sharedOperations.http.gameServerFailed", { command }), {
      toastId: "connectionError",
    });
  } else {
    const res = await response.json();
    if (res.failed === true) {
      toast.warning(
        i18n.t("sharedOperations.http.commandFailed", {
          command,
          result: JSON.stringify(res.result),
          error: res.error,
        })
      );
      return res;
    } else if (showSuccess === true) {
      toast.success(i18n.t("sharedOperations.http.done", { command }));
    }
    try {
      if (res.forward_results) {
        res.forward_results.forEach((r) => {
          if (r.response.failed === true) {
            toast.warning(i18n.t("sharedOperations.http.forwardedFailure", { host: r.host, command }));
          } else if (r.response.failed === false && showSuccess === true) {
            toast.success(i18n.t("sharedOperations.http.forwardedSuccess", { host: r.host, command }));
          }
        });
      }
    } catch (error) {
      console.error("Error checking forwards status", error);
    }

    return res;
  }
  return response.json();
}

async function sendAction(command, parameters) {
  return postData(`${process.env.REACT_APP_API_URL}${command}`, parameters)
    .then((res) => showResponse(res, command, true))
    .catch(handle_http_errors);
}

async function _checkResult(data) {
  if (data.result) {
    let unescaped = data.result.messages.map((ele) =>
      ele.replaceAll(/\\n/g, "\n")
    );
    unescaped = unescaped.map((ele) => ele.replaceAll(/\\t/g, "\t"));
    return unescaped;
  }
  return [];
}

async function getSharedMessages(namespace) {
  return get(`get_standard_${namespace}_messages`)
    .then((res) => res.json())
    .then((res) => {
      return res;
    })
    .then(_checkResult);
}

async function addPlayerToWatchList(player_id, reason, playerName) {
  return postData(`${process.env.REACT_APP_API_URL}watch_player`, {
    player_id: player_id,
    reason: reason,
    player_name: playerName,
  })
    .then((response) =>
      showResponse(response, i18n.t("sharedOperations.http.playerWatched", { playerId: player_id }), true)
    )
    .catch(handle_http_errors);
}

async function addPlayerToBlacklist({
  blacklistId,
  playerId,
  expiresAt,
  reason,
}) {
  try {
    const response = await postData(
      `${process.env.REACT_APP_API_URL}add_blacklist_record`,
      {
        blacklist_id: blacklistId,
        player_id: playerId,
        expires_at: expiresAt || null,
        reason,
      }
    );

    return showResponse(
      response,
      i18n.t("sharedOperations.http.playerBlacklisted", { playerId }),
      true
    );
  } catch (error) {
    handle_http_errors(error);
  }
}

async function getBlacklists() {
  try {
    const response = await get("get_blacklists");
    const data = await showResponse(response, "get_blacklists", false);
    if (data.result) {
      return data.result;
    }
  } catch (error) {
    handle_http_errors(error);
  }
}

async function getServerStatus() {
  try {
    const response = await get("get_status");
    const data = await response.json();
    if (data.result) {
      return data.result;
    }
  } catch (error) {
    handle_http_errors(error);
  }
}

async function getGameState() {
  try {
    const response = await get("get_gamestate");
    const data = await response.json();
    if (data.result) {
      return data.result;
    }
  } catch (error) {
    handle_http_errors(error);
  }
}

async function getVips() {
  try {
    const response = await get("get_vip_ids");
    const data = await response.json();
    if (data.result) {
      return data.result;
    }
  } catch (error) {
    handle_http_errors(error);
  }
}

async function addPlayerVip(player) {
  try {
    const response = await execute("add_vip", player);
    const data = await showResponse(response, "add_vip", true);
    if (data.result) {
      return data.result;
    }
  } catch (error) {
    handle_http_errors(error);
  }
}

async function removePlayerVip(player) {
  try {
    const response = await execute("remove_vip", player);
    const data = await showResponse(response, "remove_vip", true);
    if (data.result) {
      return data.result;
    }
  } catch (error) {
    handle_http_errors(error);
  }
}

async function resetVotemapState() {
  try {
    const response = await execute("reset_votemap_state");
    const data = await showResponse(response, "reset_votemap_state", true);
    if (data.result) {
      return data.result;
    }
  } catch (error) {
    handle_http_errors(error);
  }
}

async function updateVotemapConfig(config) {
  try {
    const response = await execute("set_votemap_config", config);
    const data = await showResponse(response, "set_votemap_config", true);
    if (data.result) {
      return data.result;
    }
  } catch (error) {
    handle_http_errors(error);
  }
}

async function getVotemapStatus() {
  try {
    const response = await get("get_votemap_status");
    const data = await response.json();
    if (data.result) {
      return data.result;
    }
  } catch (error) {
    handle_http_errors(error);
  }
}

async function getVotemapConfig() {
  try {
    const response = await get("get_votemap_config");
    const data = await response.json();
    if (data.result) {
      return data.result;
    }
  } catch (error) {
    handle_http_errors(error);
  }
}

async function changeMap(mapId) {
  try {
    const response = await execute("set_map", { map_name: mapId });
    const data = await showResponse(response, i18n.t("sharedOperations.http.mapChanged", { mapId }), true);
    if (data.result) {
      return data.result;
    }
  } catch (error) {
    handle_http_errors(error);
  }
}

async function changeGameLayout(payload) {
  try {
    const response = await execute("set_game_layout", payload);
    const data = await showResponse(response, "set_game_layout", true);
    if (data.result) {
      return data.result;
    }
  } catch (error) {
    handle_http_errors(error);
  }
}

async function getMapObjectives() {
  try {
    const response = await get("get_objective_rows");
    const data = await response.json();
    if (data.result) {
      return data.result;
    }
  } catch (error) {
    handle_http_errors(error);
  }
}

async function getVotemapWhitelist() {
  try {
    const response = await get("get_votemap_whitelist");
    const data = await response.json();
    if (data.result) {
      return data.result;
    }
  } catch (error) {
    handle_http_errors(error);
  }
}

async function setVotemapWhitelist(payload) {
  try {
    const response = await execute("set_votemap_whitelist", {
      map_names: payload,
    });
    const data = await showResponse(response, "set_votemap_whitelist", true);
    if (data) {
      return data?.arguments?.map_names;
    }
  } catch (error) {
    handle_http_errors(error);
  }
}

async function resetVotemapWhitelist() {
  try {
    const response = await execute("reset_map_votemap_whitelist", {});
    const data = await showResponse(
      response,
      "reset_map_votemap_whitelist",
      true
    );
    if (data.result) {
      return data.result;
    }
  } catch (error) {
    handle_http_errors(error);
  }
}

export {
  postData,
  showResponse,
  get,
  handle_http_errors,
  getSharedMessages,
  PermissionError,
  AuthError,
  sendAction,
  addPlayerToWatchList,
  addPlayerToBlacklist,
  getBlacklists,
  getServerStatus,
  addPlayerVip,
  removePlayerVip,
  getVips,
  resetVotemapState,
  getVotemapStatus,
  getVotemapConfig,
  updateVotemapConfig,
  changeMap,
  changeGameLayout,
  getMapObjectives,
  getGameState,
  getVotemapWhitelist,
  setVotemapWhitelist,
  resetVotemapWhitelist,
};
