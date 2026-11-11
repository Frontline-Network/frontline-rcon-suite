import { faker } from '@faker-js/faker';
import { generateGameLog, generateGameLogs } from '../factories/gameLog';
import { createLogStackDemo } from '../data/live-log-stacks.mjs';

// In-memory storage for logs
let storedLogs = [];
let nextCursor = 1;

const initializeLogs = (gameState) => {
  if (storedLogs.length === 0) {
    storedLogs = generateGameLogs(gameState, 500);
  }
};

const generateNewLogs = (gameState, count = 10) => {
  const latestTimestamp = storedLogs.length > 0
    ? Math.max(...storedLogs.map(log => log.timestamp_ms))
    : Date.now();
  
  return Array.from({ length: count }, () => {
    const log = generateGameLog(gameState);
    const newTimestamp = new Date(latestTimestamp + faker.number.int({ min: 1000, max: 5000 }));
    return {
      ...log,
      timestamp_ms: newTimestamp.getTime(),
      event_time: newTimestamp.toISOString()
    };
  });
};

export const handleRecentLogs = (gameState, params = {}) => {
  const {
    end = 500,
    filter_action = [],
    filter_player = [],
    inclusive_filter = true
  } = params;

  const stackDemo = new URLSearchParams(window.location.search)
    .get("demo_log_stacks") === "1";
  if (stackDemo) {
    storedLogs = createLogStackDemo(
      new URLSearchParams(window.location.search).get("demo_log_stack_size")
    ).map((line, index) => ({ ...line, cursor_id: (index + 1).toString(16).padStart(64, "0") }));
  } else {
    initializeLogs(gameState);

    // Add new logs, keep the requested limit and sort most recent first.
    storedLogs = [...generateNewLogs(gameState, 10), ...storedLogs]
      .slice(0, params.cursor_mode ? 10000 : end)
      .sort((a, b) => b.timestamp_ms - a.timestamp_ms);
  }

  storedLogs = storedLogs.map((line) => line.cursor_id ? line : { ...line, cursor_id: (nextCursor++).toString(16).padStart(64, "0") });
  let page = storedLogs.slice(0, end);
  let cursor = {};
  if (params.cursor_mode) {
    const anchor = params.after || params.before;
    const index = anchor ? storedLogs.findIndex((line) => line.cursor_id === anchor) : -1;
    const reset = anchor && (index < 0 || (params.after && index > end)) ? "cursor_expired" : null;
    const start = params.before && !reset ? index + 1 : 0;
    page = params.after && !reset ? storedLogs.slice(0, index) : storedLogs.slice(start, start + end);
    cursor = { newest: page[0]?.cursor_id ?? (params.after && !reset ? params.after : null), oldest: page.at(-1)?.cursor_id ?? null, has_older: start + page.length < storedLogs.length, reset };
  }
  // Apply filters after locating cursors, just like the server.
  let filteredLogs = page;
  if (filter_action.length > 0 || filter_player.length > 0) {
    filteredLogs = page.filter(log => {
      // The real API includes/excludes action prefixes, then narrows by player.
      const actionSelected = filter_action.some(action => String(log.action).toLowerCase().startsWith(action.toLowerCase()));
      const matchesAction = filter_action.length === 0 || (inclusive_filter ? actionSelected : !actionSelected);
      const matchesPlayer = filter_player.length === 0 || 
        filter_player.includes(log.player_name_1) || 
        (log.player_name_2 && filter_player.includes(log.player_name_2));

      return matchesAction && matchesPlayer;
    });
  }

  // Extract unique actions and players from the filtered logs
  const actions = [...new Set(filteredLogs.map(log => log.action))].sort();
  const players = [...new Set([
    ...filteredLogs.map(log => log.player_name_1),
    ...filteredLogs.map(log => log.player_name_2).filter(Boolean)
  ])].sort();

  return {
    result: {
      ...cursor,
      actions,
      players,
      logs: filteredLogs
    }
  };
};

export const handleRecentLogsSummary = (gameState, params = {}) => {
  const perActionLimit = Math.min(
    Math.max(Number.parseInt(params.per_action_limit, 10) || 100, 1),
    500
  );
  const recentLogs = handleRecentLogs(gameState, {
    end: Math.min(Math.max(Number.parseInt(params.end, 10) || 15_000, 0), 100_000),
  }).result.logs;
  const groups = new Map();
  const adminLogs = [];

  const project = (log) => ({
    player_id_1: log.player_id_1,
    player_name_1: log.player_name_1,
    player_id_2: log.player_id_2,
    player_name_2: log.player_name_2,
    message: log.message,
    timestamp_ms: log.timestamp_ms,
    action: log.action,
  });

  recentLogs.forEach((log) => {
    if (!log?.action) return;

    if (!groups.has(log.action)) groups.set(log.action, []);
    const group = groups.get(log.action);
    const projected = project(log);
    if (group.length < perActionLimit) group.push(projected);

    if (log.action.startsWith("CHAT") && (log.message || "").includes("!admin")) {
      adminLogs.push(projected);
    }
  });

  return {
    result: {
      groups: [...groups].map(([group, logs]) => ({ group, logs })),
      admin_logs: adminLogs,
    },
  };
};
