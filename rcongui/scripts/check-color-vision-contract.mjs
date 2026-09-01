import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import {
  getThemeTeamColor,
  getThemeTeamColors,
} from "../src/themes/teamColors.js";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const root = resolve(scriptDirectory, "..");
const colorVisionPalettes = {
  standard: { info: "#6f9ea3", error: "#c55f51" },
  deuteranopia: { info: "#56b4e9", error: "#d55e00" },
  protanopia: { info: "#56b4e9", error: "#cc79a7" },
  tritanopia: { info: "#cc79a7", error: "#d55e00" },
};
const appearanceSource = await readFile(
  resolve(root, "src/themes/appearance.js"),
  "utf8"
);

for (const [mode, palette] of Object.entries(colorVisionPalettes)) {
  assert.match(appearanceSource, new RegExp(`${mode}:\\s*\\{`));
  assert.ok(
    appearanceSource.includes(`info: "${palette.info}"`) &&
      appearanceSource.includes(`error: "${palette.error}"`),
    `${mode}: expected semantic colors are missing from the appearance palette`
  );
  const theme = {
    palette: {
      info: { main: palette.info },
      error: { main: palette.error },
      text: { secondary: "#777777" },
    },
  };
  const teamColors = getThemeTeamColors(theme);

  assert.equal(
    teamColors.allies,
    palette.info,
    `${mode}: allies must use info`
  );
  assert.equal(teamColors.axis, palette.error, `${mode}: axis must use error`);
  assert.notEqual(
    teamColors.allies,
    teamColors.axis,
    `${mode}: team colors must remain distinguishable`
  );
  assert.equal(getThemeTeamColor(theme, "Allies"), palette.info);
  assert.equal(getThemeTeamColor(theme, "Axis"), palette.error);
}

const themedBalanceFiles = [
  "src/components/LiveLogs/LogLine.jsx",
  "src/components/game/overview.jsx",
  "src/components/game/shapes.jsx",
  "src/components/shared/TeamBalanceBar.jsx",
  "src/pages/settings/[configs]/autobalancer-history-dashboard.jsx",
  "src/pages/settings/[configs]/autobalancer-round-history.jsx",
  "src/pages/settings/[configs]/autobalancer-shadow-charts.jsx",
  "src/pages/views/team/autobalancer-card.jsx",
  "src/pages/views/team/battle-summary.jsx",
  "src/pages/views/team/styled.jsx",
  "src/pages/views/live/logs-columns.jsx",
];
const legacyBalanceColors =
  /#(?:65a9d6|ed6259|4f91cb|d25a4f|6f9ea3|c55f51|2563eb|d97706|64748b|0f766e|7c3aed)|rgba\((?:33,150,243|244,67,54|66,165,245|239,83,80|101,169,214|237,98,89)|@mui\/material\/colors/i;

for (const relativePath of themedBalanceFiles) {
  const source = await readFile(resolve(root, relativePath), "utf8");
  assert.doesNotMatch(
    source,
    legacyBalanceColors,
    `${relativePath} must not bypass the active color-vision palette`
  );
}

console.log("Color-vision theme contract passed.");
