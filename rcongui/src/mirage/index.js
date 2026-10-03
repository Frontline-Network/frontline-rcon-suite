import { createServer, Response } from "miragejs";
// Snapshot of get_api_documentation from this source tree (2026-10-03).
// Used only by the fake preview; production always requests its own backend.
import apiDocumentation from "./data/api-documentation.json";
import { normalizeAppearance } from "../themes/appearance";
import { normalizeLiveViewPreferences } from "../pages/views/live/live-view-preferences.mjs";
import { handleTeamView } from "./routes/team-view";
import { createGameState } from "./state/game";
import {
  handleRecentLogs,
  handleRecentLogsSummary,
} from "./routes/recent-logs";
import {
  autobalancerConfig,
  autobalancerHistoryDashboard,
  autobalancerRoundArchive,
  autobalancerSchema,
  autobalancerShadowOverview,
  autobalancerStatus,
  reviewAutobalancerShadowDecision,
} from "./data/autobalancer";
import {
  getDemoServerConnection,
  getDemoTeamView,
  demoPlayerRecords,
  demoVietnamMapLayers,
  getDemoServerList,
  getDemoServerStatus,
  getDemoRole,
  isDemoAuthenticated,
  isDemoSessionExpired,
  getDemoSystemUsage,
} from "./demo-data";

export function makeServer({ environment = "development" } = {}) {
  let gameState = createGameState();
  let demoServerName = "[GER] Frontline Network | #2";
  let demoServerNameConfig = { ip: "127.0.0.1", port: 10011 };
  const disbandAttempts = new Map();
  const ok = (result) => ({ result });
  const protectedRequestLog = [];
  let demoDiscordLastTest = null;
  let demoDiscordEnabled = true;
  let demoIncidents = [
    {
      id: "demo-report-1",
      server_number: 2,
      source: "chat",
      status: "new",
      reporter_id: "76561198000000001",
      reporter_name: "FLN_Raven",
      target_id: "76561198000000004",
      target_name: "FLN_Hawkeye",
      reason: "Absichtlicher Teamkill am mittleren Punkt.",
      raw_message: "!admin hawkeye absichtlicher tk",
      assigned_to: null,
      revision: 1,
      created_at: new Date(Date.now() - 4 * 60000).toISOString(),
      updated_at: new Date(Date.now() - 4 * 60000).toISOString(),
      subjects: [],
      primary_subject: null,
    },
    {
      id: "demo-report-2",
      server_number: 3,
      source: "chat",
      status: "claimed",
      reporter_id: "76561198000000002",
      reporter_name: "FLN_Wolf",
      target_id: null,
      target_name: null,
      reason: "Squad Able spricht nicht und reagiert nicht auf den Commander.",
      raw_message: "!admin squad able redet nicht",
      assigned_to: "Frontline Admin",
      revision: 2,
      created_at: new Date(Date.now() - 12 * 60000).toISOString(),
      updated_at: new Date(Date.now() - 2 * 60000).toISOString(),
      subjects: [{ id: "subject-able", kind: "squad", name: "Able", confirmed: true }],
      primary_subject: { id: "subject-able", kind: "squad", name: "Able", confirmed: true },
    },
    {
      id: "demo-report-3",
      server_number: 4,
      source: "chat",
      status: "resolved",
      reporter_id: "76561198000000003",
      reporter_name: "FLN_Valkyrie",
      target_id: "76561198000000005",
      target_name: "FLN_Falcon",
      reason: "Beleidigungen im Teamchat.",
      raw_message: "!admin falcon beleidigt",
      assigned_to: "Leitstelle",
      revision: 4,
      created_at: new Date(Date.now() - 45 * 60000).toISOString(),
      updated_at: new Date(Date.now() - 22 * 60000).toISOString(),
      resolved_at: new Date(Date.now() - 22 * 60000).toISOString(),
      subjects: [],
      primary_subject: null,
    },
  ];
  const trackProtectedRequest = (path, handler) => (...args) => {
    protectedRequestLog.push(path);
    if (isDemoSessionExpired()) {
      return new Response(
        401,
        { "Content-Type": "application/json" },
        JSON.stringify({ error: "Session expired" })
      );
    }
    return handler(...args);
  };
  if (typeof window !== "undefined") {
    window.__CRCON_DEMO_PROTECTED_REQUESTS__ = protectedRequestLog;
  }
  const isVietnamDemo = getDemoServerConnection().game === "hll_vietnam";
  const ww2CurrentLayer = {
    id: "foy_warfare_night",
    name: "foy_warfare_night",
    pretty_name: "Foy · Warfare · Nacht",
    game_mode: "warfare",
    environment: "night",
    map: {
      pretty_name: "Foy",
      attackers: null,
      allies: { name: "us", team: "Alliierte" },
      axis: { name: "ger", team: "Achsenmächte" },
    },
  };
  const ww2NextLayer = {
    ...ww2CurrentLayer,
    id: "carentan_warfare",
    name: "carentan_warfare",
    pretty_name: "Carentan · Warfare",
    environment: "day",
    map: { ...ww2CurrentLayer.map, pretty_name: "Carentan" },
  };
  const ww2MapLayers = [
    { ...ww2CurrentLayer, image_name: "foy-night.webp", map: { ...ww2CurrentLayer.map, orientation: "vertical" } },
    { ...ww2NextLayer, image_name: "carentan-day.webp", map: { ...ww2NextLayer.map, orientation: "horizontal" } },
    {
      ...ww2CurrentLayer,
      id: "kursk_offensive_ger",
      name: "kursk_offensive_ger",
      pretty_name: "Kursk · Offensive · Deutschland",
      game_mode: "offensive",
      environment: "day",
      attackers: "ger",
      image_name: "kursk-day.webp",
      map: { ...ww2CurrentLayer.map, pretty_name: "Kursk", orientation: "horizontal" },
    },
    {
      ...ww2CurrentLayer,
      id: "mortain_skirmish_day",
      name: "mortain_skirmish_day",
      pretty_name: "Mortain · Skirmish",
      game_mode: "skirmish",
      environment: "day",
      image_name: "mortain-day.webp",
      map: { ...ww2CurrentLayer.map, pretty_name: "Mortain", orientation: "vertical" },
    },
  ];
  const mapLayers = isVietnamDemo ? demoVietnamMapLayers : ww2MapLayers;
  const currentLayer = isVietnamDemo ? demoVietnamMapLayers[4] : ww2CurrentLayer;
  const nextLayer = isVietnamDemo ? demoVietnamMapLayers[3] : ww2NextLayer;
  const collectPlayers = () => ["axis", "allies"].flatMap((team) => [
    ...(gameState[team].commander ? [gameState[team].commander] : []),
    ...Object.values(gameState[team].squads).flatMap((squad) => squad.players),
  ]);
  const demoPlayerNames = ["FLN_Raven", "FLN_Wolf", "FLN_Valkyrie", "FLN_Hawkeye", "FLN_Falcon", "FLN_Bravo"];
  const playerComments = new Map();
  const playerRecords = () => demoPlayerNames.map((name, index) => ({
    id: index + 1,
    player_id: `7656119800000000${index + 1}`,
    names: [{ name, created: new Date(Date.now() - (index + 20) * 86400000).toISOString(), last_seen: new Date().toISOString() }],
    soldier: { name, level: 80 + index * 17, clan_tag: "FLN", platform: "steam" },
    account: { name, country: index % 2 ? "AT" : "DE" },
    country: index % 2 ? "AT" : "DE",
    first_seen_timestamp_ms: Date.now() - (index + 20) * 86400000,
    last_seen_timestamp_ms: Date.now() - index * 1800000,
    created: new Date(Date.now() - (index + 20) * 86400000).toISOString(),
    total_playtime_seconds: 28800 + index * 3600,
    current_playtime_seconds: index < 3 ? 3600 : 0,
    penalty_count: { PUNISH: index, KICK: index % 2, TEMPBAN: 0, PERMABAN: 0 },
    flags: index === 2 ? [{ id: 1, flag: "Teamplay", comment: "Verlässlich", modified: new Date().toISOString() }] : [],
    received_actions: index % 2 ? [
      { action_type: "KICK", reason: "Regelhinweis", by: "Frontline Admin", time: new Date(Date.now() - index * 86400000).toISOString() },
    ] : [
      { action_type: "PUNISH", reason: "Teamkill", by: "Leitstelle", time: new Date(Date.now() - index * 7200000).toISOString() },
    ],
    sessions: [
      { start: new Date(Date.now() - (index + 2) * 7200000).toISOString(), end: new Date(Date.now() - (index + 2) * 7200000 + 5400000).toISOString() },
      { start: new Date(Date.now() - (index + 5) * 86400000).toISOString(), end: null },
    ],
    comments: playerComments.get(`7656119800000000${index + 1}`) ?? [
      { content: "Demo-Notiz für die Moderation.", by: "Frontline Admin", creation_time: new Date(Date.now() - index * 3600000).toISOString() },
    ],
    sessions_count: 4 + index,
    watchlist: index === 2 ? { is_watched: true, reason: "Beobachtung", count: 1 } : null,
    vips: index === 0 ? [{ server_number: 2, expiration: new Date(Date.now() + 86400000 * 30).toISOString() }] : [],
    blacklist: null,
    steaminfo: null,
  }));
  const scorePlayers = () => demoPlayerNames.map((name, index) => {
    const kills = 28 - index;
    const deaths = 4 + (index % 9);
    const timeSeconds = 4200 - index * 40;
    return {
      player_id: `7656119800000000${index + 1}`,
      player: name,
      team: index % 2 ? "axis" : "allies",
      role: index === 0 ? "officer" : "rifleman",
      unit: index % 2 ? "Baker" : "Able",
      level: 80 + index * 17,
      kills,
      deaths,
      combat: 540 - index * 8,
      offense: 310 - index * 4,
      defense: 280 - index * 3,
      support: 420 - index * 5,
      kills_streak: Math.max(1, 9 - (index % 8)),
      time_seconds: timeSeconds,
      kill_death_ratio: Number((kills / deaths).toFixed(2)),
      kills_per_minute: Number((kills / (timeSeconds / 60)).toFixed(2)),
      teamkills: index % 3,
      teamkills_streak: index % 2,
      deaths_by_tk: index % 2,
      deaths_by_tk_streak: index % 2,
      steaminfo: { country: index % 2 ? "AT" : "DE" },
    };
  });
  const liveScorePlayers = () => Array.from({ length: 36 }, (_, index) => {
    const base = scorePlayers()[index % demoPlayerNames.length];
    const team = index % 2 ? "axis" : "allies";
    const kills = Math.max(0, 34 - index);
    const deaths = 3 + (index % 11);
    return {
      ...base,
      player_id: `${base.player_id.slice(0, -2)}${String(index + 1).padStart(2, "0")}`,
      player: index < demoPlayerNames.length ? base.player : `${base.player}_${index + 1}`,
      team,
      faction: team === "allies" ? "us" : "ger",
      status: index % 7 === 0 ? "offline" : index % 5 === 0 ? "idle" : "online",
      kills,
      deaths,
      teamkills: index % 9 === 0 ? 2 : index % 5 === 0 ? 1 : 0,
      kills_streak: Math.max(1, 10 - (index % 8)),
      kill_death_ratio: Number((kills / Math.max(1, deaths)).toFixed(2)),
      kills_per_minute: Number((kills / (58 + (index % 30))).toFixed(2)),
      time_seconds: Math.max(420, 4080 - index * 88),
      combat: 610 - index * 9,
      offense: 340 - index * 4,
      defense: 300 - index * 3,
      support: 460 - index * 5,
      weapons: { "M1 GARAND": Math.max(1, kills - 4), "MK2 GRENADE": index % 5 },
      most_killed: { [scorePlayers()[(index + 1) % demoPlayerNames.length].player_id]: 4 + (index % 5) },
      death_by: { [scorePlayers()[(index + 2) % demoPlayerNames.length].player_id]: 2 + (index % 4) },
    };
  });
  const autoMod = (enabled, webhook = false) => ({
    enabled,
    discord_webhook_url: webhook ? "https://discord.example/frontline" : "",
  });
  
  const server = createServer({
    environment,

    routes() {
      this.urlPrefix = process.env.REACT_APP_API_URL;

      // A complete, deterministic shell for visual development and demos.
      this.get("/is_logged_in", () => {
        const authenticated = isDemoAuthenticated();
        return ok({
          authenticated,
          username: authenticated ? "Frontline Admin" : "",
        });
      });
      this.post("/login", () => ok({ authenticated: true, username: "Frontline Admin" }));
      this.get(
        "/get_own_user_permissions",
        trackProtectedRequest("/api/get_own_user_permissions", () => {
          const isViewer = getDemoRole() === "viewer";
          return ok({
            user_name: isViewer ? "Frontline Viewer" : "Frontline Admin",
            is_superuser: !isViewer,
            is_staff: !isViewer,
            permissions: [],
          });
        })
      );
      const demoAppearances = new Map();
      const appearanceStorageKey = () => `crcon.demo.appearance.${getDemoRole()}`;
      this.get(
        "/get_own_user_appearance",
        trackProtectedRequest("/api/get_own_user_appearance", () => {
          const key = appearanceStorageKey();
          let saved = demoAppearances.get(key);
          try {
            saved = JSON.parse(localStorage.getItem(key)) || saved;
          } catch { /* use the in-memory fallback when storage is unavailable */ }
          return ok(normalizeAppearance(saved));
        })
      );
      this.put(
        "/set_own_user_appearance",
        trackProtectedRequest("/api/set_own_user_appearance", (_schema, request) => {
          const appearance = normalizeAppearance(JSON.parse(request.requestBody || "{}"));
          const key = appearanceStorageKey();
          demoAppearances.set(key, appearance);
          try {
            localStorage.setItem(key, JSON.stringify(appearance));
          } catch { /* keep the in-memory fallback */ }
          return ok(appearance);
        })
      );
      this.get("/logout", () => ok(true));
      const liveViewStorageKey = () => `crcon.demo.live-view.${getDemoRole()}`;
      this.get(
        "/get_own_user_live_view",
        trackProtectedRequest("/api/get_own_user_live_view", () => {
          if (new URLSearchParams(window.location.search).get("demo_live_view_error") === "load") {
            return new Response(503, {}, { error: "Demo settings load failed" });
          }
          let preferences;
          try {
            preferences = JSON.parse(localStorage.getItem(liveViewStorageKey()));
          } catch { /* use defaults */ }
          return ok(normalizeLiveViewPreferences(preferences));
        })
      );
      this.put(
        "/set_own_user_live_view",
        trackProtectedRequest("/api/set_own_user_live_view", (_schema, request) => {
          if (new URLSearchParams(window.location.search).get("demo_live_view_error") === "save") {
            return new Response(503, {}, { error: "Demo settings save failed" });
          }
          const preferences = normalizeLiveViewPreferences(JSON.parse(request.requestBody));
          localStorage.setItem(liveViewStorageKey(), JSON.stringify(preferences));
          return ok(preferences);
        })
      );

      this.get(
        "/get_connection_info",
        trackProtectedRequest("/api/get_connection_info", () =>
          ok(getDemoServerConnection())
        )
      );
      this.get(
        "/get_server_list",
        trackProtectedRequest("/api/get_server_list", () =>
          ok(getDemoServerList())
        )
      );
      this.get(
        "/get_status",
        trackProtectedRequest("/api/get_status", () =>
          ok(getDemoServerStatus())
        )
      );
      this.get(
        "/get_gamestate",
        trackProtectedRequest("/api/get_gamestate", () =>
          ok({
            current_map: currentLayer,
            next_map: nextLayer,
            raw_time_remaining: "00:57:07",
            time_remaining: 3427,
            allied_score: 3,
            axis_score: 2,
            num_allied_players: 49,
            num_axis_players: 49,
          })
        )
      );
      this.get(
        "/get_ingame_mods",
        trackProtectedRequest("/api/get_ingame_mods", () => ok([]))
      );
      this.get(
        "/get_online_mods",
        trackProtectedRequest("/api/get_online_mods", () => ok([]))
      );
      this.get("/get_system_usage", () => ok(getDemoSystemUsage()));
      this.get("/get_version", () => ok("11.2.0"));
      this.get("/get_api_documentation", () => ok(apiDocumentation));
      this.get(
        "/get_name",
        trackProtectedRequest("/api/get_name", () => ok(demoServerName))
      );
      this.post(
        "/set_server_name",
        trackProtectedRequest("/api/set_server_name", (_schema, request) => {
          const payload = JSON.parse(request.requestBody || "{}");
          demoServerName = String(payload.name || "").trim();
          return ok(demoServerName);
        })
      );
      this.get(
        "/get_server_name_change_config",
        trackProtectedRequest("/api/get_server_name_change_config", () =>
          ok(demoServerNameConfig)
        )
      );
      this.post(
        "/set_server_name_change_config",
        trackProtectedRequest(
          "/api/set_server_name_change_config",
          (_schema, request) => {
            const payload = JSON.parse(request.requestBody || "{}");
            demoServerNameConfig = {
              ip: String(payload.ip || "").trim(),
              port: Number(payload.port),
            };
            return ok(demoServerNameConfig);
          }
        )
      );

      this.get("/mobile/v1/devices", () => ok([]));
      this.get("/mobile/v1/bootstrap", () => ok({
        user: { permissions: [] },
        mobile_configuration: {
          public_base_url: "https://demo.crcon.invalid",
          incident_triggers: ["!admin"],
          incident_retention_days: 30,
          push_relay_configured: false,
        },
      }));

      const isDiscordDemoConnected = () =>
        typeof window !== "undefined" &&
        new URLSearchParams(window.location.search).get("demo_discord") ===
          "connected";
      const demoDiscordIntegration = () => {
        const connected = isDiscordDemoConnected();
        return {
          installation_id: "00000000-0000-4000-8000-000000000002",
          enabled: connected && demoDiscordEnabled,
          connected,
          guild_id: connected ? "123456789012345678" : "",
          guild_name: connected ? "Frontline Network" : "",
          channel_id: connected ? "234567890123456789" : "",
          channel_name: connected ? "admin-reports" : "",
          moderator_role_ids: connected ? ["345678901234567890"] : [],
          allowed_actions: [
            "message",
            "punish",
            "kick",
            "temp_ban",
            "perma_ban",
          ],
          language: "de",
          has_api_key: false,
          api_model_options: [
            { id: "gpt-5.6-luna", name: "GPT-5.6 Luna" },
            { id: "gpt-5.4-nano", name: "GPT-5.4 Nano" },
          ],
          ai_config: {
            chat_enabled: false,
            names_enabled: false,
            shadow_mode: true,
            quality_opt_in: false,
            provider: "api_key",
          },
          policy: {
            custom_terms: [],
            exceptions: [],
            custom_regexes: [],
            hard_rule_ids: [],
          },
          reporter_templates: {},
        };
      };
      this.get("/discord/v1/integration", () => ok(demoDiscordIntegration()));
      this.put("/discord/v1/integration", (schema, request) => {
        const payload = JSON.parse(request.requestBody || "{}");
        demoDiscordEnabled = Boolean(payload.enabled);
        return ok({
          ...demoDiscordIntegration(),
          ...payload,
          connected: isDiscordDemoConnected(),
        });
      });
      this.del("/discord/v1/integration", () => {
        demoDiscordEnabled = false;
        return ok({
          ...demoDiscordIntegration(),
          enabled: false,
          connected: false,
        });
      });
      this.get("/discord/v1/options", () =>
        ok({
          guild: isDiscordDemoConnected()
            ? { id: "123456789012345678", name: "Frontline Network" }
            : null,
          channels: isDiscordDemoConnected()
            ? [
                { id: "234567890123456789", name: "admin-reports" },
                { id: "234567890123456790", name: "moderation" },
              ]
            : [],
          roles: isDiscordDemoConnected()
            ? [
                { id: "345678901234567890", name: "Moderator" },
                { id: "345678901234567891", name: "Discord Admin" },
              ]
            : [],
        })
      );
      this.get("/discord/v1/status", () =>
        ok({
          setup_state: demoDiscordEnabled ? "active" : "paused",
          enabled: demoDiscordEnabled,
          connected: isDiscordDemoConnected(),
          service_configured: true,
          callback_mode: "broker",
          delivery: {
            state: "delivered",
            last_delivered_at: new Date(Date.now() - 120000).toISOString(),
            last_attempt_at: new Date(Date.now() - 120000).toISOString(),
            pending_count: 0,
            error_code: null,
          },
          last_test: demoDiscordLastTest || {
            state: "unknown",
            checked_at: null,
            error_code: null,
          },
          last_diagnostic: {
            checked_at: new Date().toISOString(),
            result: isDiscordDemoConnected()
              ? {
                  state: "healthy",
                  checked_at: new Date().toISOString(),
                  service: { state: "online", latency_ms: 18 },
                  discord_binding: {
                    state: "online",
                    guild_name: "Frontline Network",
                    channel_name: "admin-reports",
                    latency_ms: 24,
                  },
                  callback: {
                    state: "online",
                    transport: "broker",
                    latency_ms: 31,
                  },
                }
              : null,
          },
        })
      );
      this.post("/discord/v1/diagnostics", () => ok({ state: "healthy" }));
      this.post("/discord/v1/test-message", () => {
        demoDiscordLastTest = {
          state: "succeeded",
          checked_at: new Date().toISOString(),
          error_code: null,
        };
        return ok({ sent: true });
      });
      this.get("/discord/v1/ai/status", () =>
        ok({
          state: "disabled",
          available: false,
          connected: false,
          models: [],
        })
      );

      this.get("/get_server_settings", () => {
        const unavailable =
          typeof window !== "undefined" &&
          new URLSearchParams(window.location.search).get(
            "demo_settings_error"
          ) === "1";
        if (unavailable) {
          return new Response(
            503,
            { "Content-Type": "application/json" },
            { error: "Demo server settings unavailable" }
          );
        }
        return ok({
          autobalance_enabled: true,
          votekick_enabled: true,
          team_switch_cooldown: 15,
          autobalance_threshold: 3,
          idle_autokick_time: 15,
          max_ping_autokick: 250,
          queue_length: 6,
          vip_slots_num: 2,
        });
      });
      this.get("/get_services", () => ok([
        { name: "rcon", statename: "RUNNING", start: 1775205000, stop: 0, now: 1775210400, info: "RCON-Verbindung zum Gameserver" },
        { name: "worker", statename: "RUNNING", start: 1775205000, stop: 0, now: 1775210400, info: "CRCON-Auftragsverarbeitung" },
        { name: "scheduler", statename: "RUNNING", start: 1775205000, stop: 0, now: 1775210400, info: "Zeitgesteuerte Automatisierungen" },
        { name: "discord-bot", statename: "STOPPED", start: 1775100000, stop: 1775200000, now: 1775210400, info: "Discord-Benachrichtigungen" },
      ]));
      this.get("/get_maps", () => ok(mapLayers));
      this.get("/get_available_weapons", () =>
        ok({
          game: "hll",
          weapons: [
            { name: "155MM HOWITZER [M114]", type: "artillery" },
            { name: "150MM HOWITZER [sFH 18]", type: "artillery" },
            {
              name: "122MM HOWITZER [M1938 (M-30)]",
              type: "artillery",
            },
            {
              name: "QF 25-POUNDER [QF 25-Pounder]",
              type: "artillery",
            },
            { name: "BOMBING RUN", type: "commander" },
            { name: "PRECISION STRIKE", type: "commander" },
            { name: "STRAFING RUN", type: "commander" },
            { name: "M1 GARAND", type: "infantry" },
            { name: "KARABINER 98K", type: "infantry" },
            { name: "MP40", type: "infantry" },
            { name: "MG42", type: "machine_gun" },
            { name: "57MM CANNON [M1 57mm]", type: "pak" },
            { name: "75MM CANNON [PAK 40]", type: "pak" },
            { name: "SATCHEL", type: "satchel" },
          ],
        })
      );
      this.get("/get_available_player_flags", () =>
        ok({
          flags: [
            { flag: "admin", player_count: 18 },
            { flag: "trusted", player_count: 9 },
            { flag: "name-filter-exempt", player_count: 4 },
            { flag: "⭐", player_count: 2 },
          ],
        })
      );
      this.get("/get_map", () => ok(currentLayer));
      this.get("/get_map_rotation", () => ok({ maps: mapLayers.slice(0, 3), current_index: 0, next_index: 1 }));
      this.get("/get_map_shuffle_enabled", () => ok(false));
      this.get("/get_objective_rows", () => ok([
        ["Road to Recourt", "Southern Edge", "Dugout Barn"],
        ["Foy", "West Bend", "Cobru Factory"],
        ["Flak Position", "Eastern Ourthe", "Bizory-Foy Road"],
        ["N30 Highway", "Train Line", "Foy Outskirts"],
        ["Cobru Approach", "Foy Road", "Forest Outskirts"],
      ]));
      this.get("/get_votemap_whitelist", () => ok(mapLayers.slice(0, 3).map((map) => map.id)));
      this.get("/get_votemap_status", () => ok(mapLayers.slice(0, 3).map((map, index) => ({
        map,
        voters: ["FLN_Raven", "FLN_Hawkeye", "FLN_Falcon", "FLN_Bravo"].slice(0, 4 - index),
      }))));
      this.get("/get_votemap_config", () => ok({ enabled: true, reminder_frequency_minutes: 5, num_warfare_options: 2, num_offensive_options: 1, num_conquest_options: 1, num_domination_options: 1, num_skirmish_control_options: 0, number_last_played_to_exclude: 2, default_method: "least_played_from_suggestions", instruction_text: "Stimme mit !votemap ab: {map_selection}", thank_you_text: "Danke {player_name}.", help_text: "Nutze !votemap <Nummer>." }));

      const completedGames = [0, 1, 2, 3].map((index) => ({
        id: `fln-demo-${index + 1}`,
        server_number: 2,
        map: mapLayers[index % mapLayers.length],
        result: { allied: index % 2 ? 2 : 3, axis: index % 2 ? 3 : 2 },
        start: new Date(Date.now() - (index + 1) * 7200000).toISOString(),
        end: new Date(Date.now() - (index + 1) * 7200000 + 5400000).toISOString(),
      }));
      this.get("/get_scoreboard_maps", () => ok({ maps: completedGames, total: completedGames.length }));
      this.get("/get_map_scoreboard", (schema, request) => {
        const game = completedGames.find((item) => item.id === request.queryParams.map_id) || completedGames[0];
        return ok({ ...game, player_stats: scorePlayers() });
      });
      this.get("/get_live_game_stats", () => ok({
        stats: liveScorePlayers(),
        snapshot_timestamp: Math.floor(Date.now() / 1000),
        refresh_interval_sec: 15,
      }));
      this.get("/get_public_info", () => ok({
        time_remaining: 3427,
        score: { allied: 3, axis: 2 },
        current_map: { map: currentLayer, start: Math.floor(Date.now() / 1000) - 3600 },
        next_map: { map: mapLayers[1], start: null },
        player_count: 86,
        max_player_count: 100,
        player_count_by_team: { allied: 43, axis: 43 },
      }));

      this.post("/get_players_history", () => ({ result: { players: playerRecords(), total: playerRecords().length } }));
      this.get("/get_player_profile", (schema, request) => {
        const records = new URLSearchParams(window.location.search).get("demo_warning_sources") === "1"
          ? demoPlayerRecords
          : playerRecords();
        const player = records.find(
          (entry) => entry.player_id === request.queryParams.player_id,
        );
        return player
          ? ok(player)
          : new Response(JSON.stringify({ error: "Player not found" }), {
              status: 404,
              headers: { "Content-Type": "application/json" },
            });
      });
      this.get("/get_player_messages", () => ok([]));
      this.get("/get_message_templates", () => ok([
        {
          id: 1,
          title: "Regelhinweis",
          category: "MESSAGE",
          message: "Bitte beachte die Serverregeln.",
        },
      ]));
      this.post("/post_player_comment", (schema, request) => {
        const payload = JSON.parse(request.requestBody || "{}");
        if (!payload.player_id || !payload.comment?.trim()) {
          return new Response(JSON.stringify({ error: "Invalid comment" }), {
            status: 400,
            headers: { "Content-Type": "application/json" },
          });
        }
        const existing = playerComments.get(payload.player_id) ?? [];
        playerComments.set(payload.player_id, [
          {
            content: payload.comment.trim(),
            by: "Frontline Admin",
            creation_time: new Date().toISOString(),
          },
          ...existing,
        ]);
        return ok(true);
      });
      this.get("/get_bans", () => ok([]));
      this.post("/get_historical_logs", () => ({ result: demoPlayerNames.map((name, index) => ({
        id: index + 1,
        type: index % 3 === 0 ? "CHAT[Team]" : index % 3 === 1 ? "KILL" : "CONNECTED",
        event_time: new Date(Date.now() - index * 90000).toISOString(),
        creation_time: new Date(Date.now() - index * 90000).toISOString(),
        content: index % 3 === 0 ? `${name}: Bereit für den Einsatz.` : name,
        player1_id: `7656119800000000${index + 1}`,
        player1_name: name,
        player2_id: null,
        player2_name: null,
        server: "2",
        raw: `[FLN] ${name}`,
      })) }));
      this.get("/get_audit_logs", () => ok({
        audit_logs: [
          { creation_time: new Date().toISOString(), username: "Frontline Admin", command: "message_player", command_arguments: JSON.stringify({ player_name: "FLN_Raven", player_id: "76561198000000001", message: "Bitte beachte die Serverregeln." }) },
          { creation_time: new Date(Date.now() - 3600000).toISOString(), username: "Leitstelle", command: "set_map", command_arguments: JSON.stringify({ map_name: "foy_warfare_night" }) },
        ],
        total_pages: 1, page: 1, page_size: 10, total_entries: 2,
      }));
      this.get("/get_audit_logs_autocomplete", () => ok({ usernames: ["Frontline Admin", "Leitstelle"], commands: ["message_player", "set_map"] }));
      this.get("/get_admin_ids", () => ok([
        { player_id: "76561198000000001", name: "FLN_Raven", role: "senior" },
        { player_id: "76561198000000002", name: "FLN_Wolf", role: "spectator" },
      ]));
      this.get("/get_admin_groups", () => ok(["spectator", "junior", "senior"]));
      this.get("/get_vip_ids", () => ok([
        { player_id: "76561198000000001", name: "FLN_Raven", vip_expiration: null },
        { player_id: "76561198000000002", name: "FLN_Wolf", vip_expiration: new Date(Date.now() + 86400000 * 30).toISOString() },
        { player_id: "76561198000000003", name: "FLN_Valkyrie", vip_expiration: new Date(Date.now() + 86400000 * 7).toISOString() },
        { player_id: "76561198000000004", name: "FLN_OldGuard", vip_expiration: new Date(Date.now() - 86400000 * 2).toISOString() },
      ]));
      this.get("/download_vips", () =>
        new Response(
          200,
          { "Content-Type": "text/plain" },
          [
            "76561198000000001 FLN_Raven",
            "76561198000000002 FLN_Wolf",
            "76561198000000003 FLN_Valkyrie",
            "76561198000000004 FLN_OldGuard",
          ].join("\n")
        )
      );
      this.post("/upload_vips", () => ({ failed: false, result: "OK" }));
      this.get("/upload_vips_result", () =>
        ok({
          status: "finished",
          result: ["4 VIP-Einträge wurden im Demo-Modus verarbeitet."],
        })
      );
      const demoBlacklists = [
        { id: 1, name: "FLN Hauptsperrliste", servers: null, sync: "ban_on_connect" },
        { id: 2, name: "Event-Ausschlüsse", servers: [2], sync: "kick_only" },
      ];
      this.get("/get_blacklists", () => ok(demoBlacklists));
      this.get("/get_blacklist_records", () => ok({
        records: [
          {
            id: 101,
            blacklist: demoBlacklists[0],
            player: { player_id: "76561198000000021", names: [{ name: "FLN_Rulebreaker" }], steaminfo: null },
            reason: "Wiederholte schwere Regelverstöße",
            formatted_reason: "Wiederholte schwere Regelverstöße",
            created_at: new Date(Date.now() - 86400000 * 12).toISOString(),
            expires_at: null,
            is_active: true,
            admin_name: "Frontline Admin",
          },
          {
            id: 102,
            blacklist: demoBlacklists[1],
            player: { player_id: "76561198000000022", names: [{ name: "FLN_EventBan" }, { name: "Old_EventBan" }], steaminfo: null },
            reason: "Event-Ausschluss nach wiederholtem Teamkilling",
            formatted_reason: "Event-Ausschluss nach wiederholtem Teamkilling",
            created_at: new Date(Date.now() - 86400000 * 3).toISOString(),
            expires_at: new Date(Date.now() + 86400000 * 4).toISOString(),
            is_active: true,
            admin_name: "Leitstelle",
          },
        ],
        total: 2,
      }));

      this.get("/get_auto_mod_seeding_config", () => ok(autoMod(true, true)));
      this.get("/get_auto_mod_no_leader_config", () => ok(autoMod(true, true)));
      this.get("/get_auto_mod_solo_tank_config", () => ok(autoMod(true)));
      this.get("/get_auto_mod_level_config", () => ok(autoMod(false)));
      this.get("/get_name_kick_config", () => ok(autoMod(true)));
      this.get("/get_vac_game_bans_config", () => ok(autoMod(true)));
      this.get("/get_seed_vip_config", () => ok(autoMod(true)));
      this.get("/get_chat_commands_config", () => ok(autoMod(true, true)));
      this.get("/get_rcon_chat_commands_config", () => ok(autoMod(true)));

      this.get("/get_autobalancer_config", () => ok(autobalancerConfig));
      this.get("/describe_autobalancer_config", () => ok(autobalancerSchema));
      this.post("/set_autobalancer_config", (schema, request) => {
        const payload = request.requestBody
          ? JSON.parse(request.requestBody)
          : {};
        Object.assign(autobalancerConfig, payload);
        return ok(autobalancerConfig);
      });
      this.post("/execute_autobalancer_squad_switch", (schema, request) => {
        protectedRequestLog.push("/api/execute_autobalancer_squad_switch");
        const payload = request.requestBody
          ? JSON.parse(request.requestBody)
          : {};
        return {
          result: { status: "executed", moves: payload.moves || [] },
          arguments: { player_id: payload.player_id },
          failed: false,
        };
      });
      this.get("/get_autobalancer_status", () =>
        ok({ ...autobalancerStatus, updated_at: new Date().toISOString() })
      );
      this.get("/get_autobalancer_shadow_overview", () =>
        ok(autobalancerShadowOverview)
      );
      this.get("/get_autobalancer_history_dashboard", () =>
        ok(autobalancerHistoryDashboard)
      );
      this.get("/get_autobalancer_round_archive", () =>
        ok(autobalancerRoundArchive)
      );
      this.post("/review_autobalancer_shadow_decision", (schema, request) => {
        const payload = request.requestBody
          ? JSON.parse(request.requestBody)
          : {};
        const decision = reviewAutobalancerShadowDecision(payload);
        if (!decision) {
          return {
            failed: true,
            error: "Shadow-Vorschlag wurde nicht gefunden",
            result: null,
          };
        }
        return ok(decision);
      });

      // The mobile client uses an origin-rooted URL, independent of the legacy
      // API prefix. Register the same absolute URL to avoid a doubled /api.
      const incidentsUrl = new URL("/api/mobile/v1/incidents", window.location.origin).href;
      this.get(incidentsUrl, () => ok(demoIncidents));
      this.patch(`${incidentsUrl}/:incidentId`, (schema, request) => {
        const payload = request.requestBody
          ? JSON.parse(request.requestBody)
          : {};
        const index = demoIncidents.findIndex(
          (incident) => incident.id === request.params.incidentId
        );
        if (index < 0) {
          return new Response(
            404,
            { "Content-Type": "application/json" },
            { error: "Incident not found" }
          );
        }
        const current = demoIncidents[index];
        if (Number(payload.revision) !== Number(current.revision)) {
          return new Response(
            409,
            { "Content-Type": "application/json" },
            { error: "Incident revision conflict" }
          );
        }
        const nextStatus =
          payload.operation === "claim"
            ? "claimed"
            : payload.operation === "resolved"
            ? "resolved"
            : payload.operation === "dismissed"
            ? "dismissed"
            : current.status;
        const updated = {
          ...current,
          status: nextStatus,
          assigned_to:
            payload.operation === "claim"
              ? "Frontline Admin"
              : current.assigned_to,
          revision: current.revision + 1,
          updated_at: new Date().toISOString(),
          resolved_at:
            nextStatus === "resolved" ? new Date().toISOString() : current.resolved_at,
        };
        demoIncidents = demoIncidents.map((incident, incidentIndex) =>
          incidentIndex === index ? updated : incident
        );
        return { failed: false, result: updated };
      });
      
      this.get(
        "/get_team_view",
        trackProtectedRequest("/api/get_team_view", () =>
          new URLSearchParams(window.location.search).has("demo_balance")
            ? ok(getDemoTeamView())
            : handleTeamView(gameState)
        )
      );

      this.post("/get_recent_logs", (schema, request) => {
        const params = request.requestBody ? JSON.parse(request.requestBody) : request.queryParams;
        const asArray = (value) => {
          if (Array.isArray(value)) return value;
          if (!value) return [];
          return JSON.parse(value);
        };
        return handleRecentLogs(gameState, {
          end: parseInt(params.end) || 500,
          filter_action: asArray(params.filter_action),
          filter_player: asArray(params.filter_player),
          inclusive_filter: params.inclusive_filter === true || params.inclusive_filter === "true",
        });
      });

      this.post("/get_recent_logs_summary", (schema, request) => {
        const params = request.requestBody
          ? JSON.parse(request.requestBody)
          : request.queryParams;
        return handleRecentLogsSummary(gameState, params);
      });

      const playerActionCommands = [
        "message_player", "message_all_players", "bulk_message_players", "set_broadcast",
        "watch_player", "unwatch_player", "add_vip", "remove_vip",
        "switch_player_now", "switch_player_on_death", "punish", "kick",
        "temp_ban", "perma_ban", "unban", "add_blacklist_record",
        "edit_blacklist_record", "delete_blacklist_record", "create_blacklist",
        "edit_blacklist", "delete_blacklist",
        "flag_player", "unflag_player", "add_admin",
        "remove_player_from_squad", "disband_squad_by_name",
      ];
      playerActionCommands.forEach((command) => {
        this.post(`/${command}`, (schema, request) => {
          const args = request.requestBody ? JSON.parse(request.requestBody) : {};
          if (command === "disband_squad_by_name") {
            const failingSquad = new URLSearchParams(window.location.search).get("demo_disband_failure");
            const attempts = disbandAttempts.get(args.squad_name) || 0;
            disbandAttempts.set(args.squad_name, attempts + 1);
            if (failingSquad === args.squad_name && attempts === 0) {
              return new Response(500, { "Content-Type": "application/json" }, {
                error: "Demo: Gameserver hat die Truppauflösung abgelehnt.",
              });
            }
          }
          return { failed: false, result: "OK", arguments: args };
        });
      });

      this.passthrough();
    },
  });

  return server;
}
