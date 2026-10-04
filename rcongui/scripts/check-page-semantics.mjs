import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(import.meta.dirname, "..");
const read = (relativePath) =>
  fs.readFileSync(path.join(ROOT, relativePath), "utf8");

const pageHeader = read("src/components/shared/PageHeader.jsx");
const pageState = read("src/components/shared/PageState.jsx");
const dashboard = read("src/pages/dashboard.jsx");
const autosettings = read("src/pages/settings/autosettings/index.jsx");
const playerHeader = read("src/components/player/profile/Header.jsx");
const playerCard = read("src/components/shared/card/PlayerCard.jsx");
const systemLayout = read(
  "src/pages/settings/system-diagnostics/SystemDiagnosticsLayout.jsx"
);
const configDetail = read("src/pages/settings/[configs]/detail.jsx");
const configFormLayout = read(
  "src/pages/settings/config-form/ConfigFormLayout.jsx"
);
const seedingWorkbenchLayout = read(
  "src/pages/settings/config-form/SeedingWorkbenchLayout.jsx"
);
const objectives = read("src/pages/settings/maps/objectives/index.jsx");
const objectivePicker = read(
  "src/pages/settings/maps/objectives/MapObjectivesPicker.jsx"
);
const votemapSettings = read(
  "src/pages/settings/maps/votemap/settings/index.jsx"
);
const controlLayout = read(
  "src/pages/settings/general-group/ControlPageLayout.jsx"
);
const apps = read("src/pages/apps/index.jsx");
const discordApp = read("src/pages/apps/discord-report-bot/index.jsx");
const autobalancer = read(
  "src/pages/settings/[configs]/autobalancer-moderator-dashboard.jsx"
);
const rotation = read("src/pages/settings/maps/rotation/index.jsx");
const liveWorkspace = read("src/pages/views/live/live-workspace.jsx");
const auditFilters = read("src/pages/records/audit-logs/AuditLogsFilters.jsx");
const gameLogFilters = read("src/pages/records/game-logs/GameLogsFilters.jsx");
const blacklistFilters = read(
  "src/components/Blacklist/BlacklistRecordsSearch.js"
);
const broadcastFields = read("src/components/shared/BroadcastFields.jsx");
const templateDetail = read("src/pages/settings/templates/detail.jsx");
const votemapBuilder = read(
  "src/pages/settings/maps/votemap/builder/index.jsx"
);
const gamesTable = read("src/pages/stats/games/game-list-table.jsx");
const liveSessions = read("src/pages/stats/live-sessions/index.jsx");
const liveGame = read("src/pages/stats/live-game/index.jsx");

assert.match(pageHeader, /component="header"/);
assert.match(pageHeader, /aria-labelledby=\{titleId\}/);
assert.match(pageHeader, /component="h1"/);

for (const state of [
  "empty",
  "error",
  "success",
  "offline",
  "conflict",
  "forbidden",
  "running",
  "partial",
  "destructive",
]) {
  assert.match(pageState, new RegExp(`${state}:`));
}
assert.match(pageState, /kind === "loading"/);
assert.match(
  pageState,
  /role=\{alertStates\.has\(kind\) \? "alert" : "status"\}/
);
assert.match(pageState, /aria-live=/);

// The shared PageHeader is checked above to render the actual H1.
assert.match(dashboard, /<PageHeader[\s\S]*?title=\{t\("dashboard\.title"\)\}/);
for (const [name, source] of [
  ["apps", apps],
  ["discord app", discordApp],
]) {
  assert.match(
    source,
    /component="h1"/,
    `${name} must expose its page title as H1`
  );
}

assert.match(playerHeader, /headingComponent = "h1"/);
assert.match(playerHeader, /component=\{headingComponent\}/);
assert.match(playerCard, /headingComponent="h2"/);

assert.match(autosettings, /<PageHeader/);
assert.match(systemLayout, /title=\{activeSection\.label\}/);
assert.match(
  configDetail,
  /embedded=\{isIntegrationHub \|\| isSystemDiagnostics\}/
);
assert.match(configFormLayout, /\{!embedded && \(/);
assert.match(seedingWorkbenchLayout, /\{!embedded && \(/);
assert.match(objectives, /<PageHeader/);
assert.match(objectives, /id="alert-dialog-title"/);
assert.match(objectives, /id="alert-dialog-description"/);
assert.match(objectivePicker, /aria-label=\{t\("maps\.objectiveGridCell"/);
assert.match(votemapSettings, /id="votemap-default-method"/);
assert.match(votemapSettings, /labelId="votemap-default-method-label"/);
assert.match(rotation, /<PageHeader/);
assert.match(liveWorkspace, /component="h1"/);
assert.match(auditFilters, /label=\{t\("records\.auditLogs\.parameters"\)\}/);
assert.match(
  gameLogFilters,
  /label=\{t\("records\.gameLogs\.timeline\.playerSearch"\)\}/
);
assert.match(blacklistFilters, /id="blacklist-filter-list-label"/);
assert.match(blacklistFilters, /labelId="blacklist-filter-list-label"/);
assert.match(blacklistFilters, /id="blacklist-filter-page-size-label"/);
assert.match(blacklistFilters, /labelId="blacklist-filter-page-size-label"/);
assert.match(votemapBuilder, /id="votemap-map-mode-label"/);
assert.match(votemapBuilder, /labelId="votemap-map-mode-label"/);
assert.match(votemapBuilder, /id="votemap-map-environment-label"/);
assert.match(votemapBuilder, /labelId="votemap-map-environment-label"/);
assert.match(templateDetail, /label=\{t\("settings\.templates\.messageTitle"\)\}/);
assert.match(
  templateDetail,
  /label=\{t\("settings\.templates\.messageContent"\)\}/
);
assert.match(broadcastFields, /label=\{t\("common\.time"\)\}/);
assert.match(broadcastFields, /label=\{t\("common\.message"\)\}/);
assert.match(gamesTable, /inputProps=\{\{ "aria-label": t\("stats\.games\.pageSize"\) \}\}/);
assert.match(
  liveSessions,
  /"aria-label": t\("stats\.liveSessions\.sorting"\)/
);
assert.match(
  liveSessions,
  /"aria-label": t\("common\.pagination\.pageSize"\)/
);
assert.match(liveGame, /"aria-label": t\("stats\.liveGame\.sorting"\)/);
assert.match(liveGame, /"aria-label": t\("stats\.liveGame\.pageSize"\)/);
assert.match(controlLayout, /id="control-page-section"/);
assert.match(controlLayout, /labelId="control-page-section-label"/);
assert.ok(
  (autobalancer.match(/component="h1"/g) ?? []).length >= 2,
  "Autobalancer overview and proposal detail must each expose an H1"
);

console.log(
  "Page semantics contract passed: headings, labelled controls and shared states stay connected."
);
