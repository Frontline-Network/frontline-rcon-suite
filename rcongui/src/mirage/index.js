import { createServer } from "miragejs";
import { handleTeamView } from "./routes/team-view";
import { createGameState } from "./state/game";
import { handleRecentLogs } from "./routes/recent-logs";
import {
  autobalancerConfig,
  autobalancerHistoryDashboard,
  autobalancerRoundArchive,
  autobalancerSchema,
  autobalancerShadowOverview,
  autobalancerStatus,
} from "./data/autobalancer";

export function makeServer({ environment = "development" } = {}) {
  let gameState = createGameState();
  const ok = (result) => ({ result });
  const currentLayer = {
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
  const nextLayer = {
    ...currentLayer,
    id: "carentan_warfare",
    name: "carentan_warfare",
    pretty_name: "Carentan · Warfare",
    environment: "day",
    map: { ...currentLayer.map, pretty_name: "Carentan" },
  };
  const mapLayers = [
    { ...currentLayer, image_name: "foy-night.webp", map: { ...currentLayer.map, orientation: "vertical" } },
    { ...nextLayer, image_name: "carentan-day.webp", map: { ...nextLayer.map, orientation: "horizontal" } },
    {
      ...currentLayer,
      id: "kursk_offensive_ger",
      name: "kursk_offensive_ger",
      pretty_name: "Kursk · Offensive · Deutschland",
      game_mode: "offensive",
      environment: "day",
      attackers: "ger",
      image_name: "kursk-day.webp",
      map: { ...currentLayer.map, pretty_name: "Kursk", orientation: "horizontal" },
    },
    {
      ...currentLayer,
      id: "mortain_skirmish_day",
      name: "mortain_skirmish_day",
      pretty_name: "Mortain · Skirmish",
      game_mode: "skirmish",
      environment: "day",
      image_name: "mortain-day.webp",
      map: { ...currentLayer.map, pretty_name: "Mortain", orientation: "vertical" },
    },
  ];
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
  const autoMod = (enabled, webhook = false) => ({
    enabled,
    discord_webhook_url: webhook ? "https://discord.example/frontline" : "",
  });
  
  const server = createServer({
    environment,

    routes() {
      this.urlPrefix = process.env.REACT_APP_API_URL;

      // A complete, deterministic shell for visual development and demos.
      this.get("/is_logged_in", () => ok({ authenticated: true, username: "Frontline Admin" }));
      this.post("/login", () => ok({ authenticated: true, username: "Frontline Admin" }));
      this.get("/get_own_user_permissions", () => ok({
        user_name: "Frontline Admin",
        is_superuser: true,
        permissions: [],
      }));
      this.get("/logout", () => ok(true));

      this.get("/get_connection_info", () => ok({
        name: "[GER] Frontline Network | #2",
        short_name: "Frontline #2",
        server_number: 2,
        port: 8010,
      }));
      this.get("/get_server_list", () => ok([]));
      this.get("/get_status", () => ok({
        name: "[GER] Frontline Network | #2",
        short_name: "Frontline #2",
        server_number: 2,
        current_players: 86,
        max_players: 100,
        queue_length: 4,
      }));
      this.get("/get_gamestate", () => ok({
        current_map: currentLayer,
        next_map: nextLayer,
        raw_time_remaining: "00:57:07",
        time_remaining: 3427,
        allied_score: 3,
        axis_score: 2,
        num_allied_players: 43,
        num_axis_players: 43,
      }));
      this.get("/get_ingame_mods", () => ok([]));
      this.get("/get_online_mods", () => ok([]));
      this.get("/get_system_usage", () => ok({
        cpu_usage: { percent: 18 },
        ram_usage: { percent: 46 },
        disk_usage: { percent: 62 },
      }));
      this.get("/get_version", () => ok("11.2.0"));

      this.get("/get_server_settings", () => ok({
        autobalance_enabled: true,
        votekick_enabled: true,
        team_switch_cooldown: 15,
        autobalance_threshold: 3,
        idle_autokick_time: 15,
        max_ping_autokick: 250,
        queue_length: 6,
        vip_slots_num: 2,
      }));
      this.get("/get_services", () => ok([
        { name: "rcon", statename: "RUNNING", start: 1775205000, stop: 0, now: 1775210400, info: "RCON-Verbindung zum Gameserver" },
        { name: "worker", statename: "RUNNING", start: 1775205000, stop: 0, now: 1775210400, info: "CRCON-Auftragsverarbeitung" },
        { name: "scheduler", statename: "RUNNING", start: 1775205000, stop: 0, now: 1775210400, info: "Zeitgesteuerte Automatisierungen" },
        { name: "discord-bot", statename: "STOPPED", start: 1775100000, stop: 1775200000, now: 1775210400, info: "Discord-Benachrichtigungen" },
      ]));
      this.get("/get_maps", () => ok(mapLayers));
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
      this.get("/get_votemap_config", () => ok({ enabled: true, reminder_frequency_minutes: 5, num_warfare_options: 2, num_offensive_options: 1, num_skirmish_control_options: 0, number_last_played_to_exclude: 2, default_method: "least_played_from_suggestions", instruction_text: "Stimme mit !votemap ab: {map_selection}", thank_you_text: "Danke {player_name}.", help_text: "Nutze !votemap <Nummer>." }));

      const completedGames = [0, 1, 2, 3].map((index) => ({
        id: `fln-demo-${index + 1}`,
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
      this.get("/get_live_game_stats", () => ok({ stats: scorePlayers() }));
      this.get("/get_public_info", () => ok({
        time_remaining: 3427,
        score: { allied: 3, axis: 2 },
        current_map: currentLayer,
        player_count_by_team: { allied: 43, axis: 43 },
      }));

      this.post("/get_players_history", () => ({ result: { players: playerRecords(), total: playerRecords().length } }));
      this.get("/get_player_profile", (schema, request) => {
        const player = playerRecords().find(
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
      this.post("/review_autobalancer_shadow_decision", () =>
        ok({ saved: true })
      );
      
      this.get("/get_team_view", () => {
        return handleTeamView(gameState);
      });

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

      const playerActionCommands = [
        "message_player", "message_all_players", "bulk_message_players",
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
          return { failed: false, result: "OK", arguments: args };
        });
      });

      this.passthrough();
    },
  });

  return server;
}
