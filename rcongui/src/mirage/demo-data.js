// The fixture module allocates demo rosters, logs and timestamps at startup.
// Keep those allocations and their data out of real installations entirely;
// even an unused static import would otherwise retain their side effects.
const fixtures =
  import.meta.env.MODE === "fake" ? await import("./demo-fixtures") : {};

export const isFakeMode = () => import.meta.env.MODE === "fake";

// These values are only consumed behind isFakeMode() checks or by Mirage.
export const {
  demoMapLayers,
  demoVietnamMapLayers,
  demoPlayerRecords,
  demoHistoricalLogs,
  demoAuditData,
  demoScorePlayers,
  demoGames,
  demoServices,
  demoTeamView,
  demoGameState,
  demoServerConnection,
  getDemoTeamView,
  getDemoConnectionMode,
  getDemoRole,
  isDemoAuthenticated,
  isDemoSessionExpired,
  shouldFailDemoServerSettings,
  getDemoServerConnection,
  getDemoMapLayers,
  getDemoGameState,
  getDemoServerList,
  demoServerStatus,
  getDemoServerStatus,
  demoSystemUsage,
  getDemoSystemUsage,
  demoServerSettings,
  demoBlacklists,
  demoBlacklistRecords,
} = fixtures;
