import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = (relativePath) =>
  fs.readFileSync(path.join(root, relativePath), "utf8").replaceAll("\r\n", "\n");

const list = read("src/pages/stats/games/game-list-table.jsx");
const dialog = read("src/pages/stats/games/saved-views-dialog.jsx");
const persistence = read("src/pages/stats/games/saved-game-views.js");
const detail = read("src/pages/stats/games/[gameId]/index.jsx");
const gameLogs = read("src/pages/records/game-logs/index.jsx");
const auditLogs = read("src/pages/records/audit-logs/index.jsx");
const services = read("src/pages/settings/services/index.jsx");

const requireText = (source, expected, message) => {
  if (!source.includes(expected)) throw new Error(message);
};

requireText(
  list,
  "<SavedGameViewsDialog",
  "The games archive must expose saved filter views."
);
requireText(
  list,
  "areGameViewFiltersEqual",
  "The active saved view must reflect the current filters."
);
requireText(
  dialog,
  "fullScreen={compact}",
  "Saved views must use a mobile task surface instead of overflowing the archive."
);
requireText(
  dialog,
  "savedViewsLocalHint",
  "Browser-local persistence must be explained to operators."
);
requireText(
  persistence,
  "sanitizeSavedGameViews",
  "Stored archive filters must be validated before use."
);
requireText(
  persistence,
  "MAX_SAVED_VIEWS = 12",
  "Saved views must remain bounded."
);
requireText(
  detail,
  'component="h1"',
  "Completed game details must retain an explicit page heading."
);
requireText(
  gameLogs,
  "<GameLogsFilters",
  "Game logs must retain their compact mobile filter workflow."
);
requireText(
  auditLogs,
  '<Drawer\n        anchor="right"',
  "Audit logs must retain their inspectable detail workflow."
);
requireText(
  services,
  "SystemDiagnosticsLayout",
  "Service diagnostics must remain consolidated in the shared operations layout."
);

console.log(
  "History workbench contract passed: bounded saved views, responsive archives, explicit game identity and inspectable log workflows stay connected."
);
