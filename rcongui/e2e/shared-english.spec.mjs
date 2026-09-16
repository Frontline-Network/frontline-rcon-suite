import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { sharedOperationsDe, sharedOperationsEn } from "../src/i18n/locales/shared-operations.js";
import { openDemoPage, VIEWPORTS } from "./helpers.mjs";

const flatten = (value, prefix = "") => Object.fromEntries(
  Object.entries(value).flatMap(([key, entry]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return typeof entry === "string"
      ? [[path, entry]]
      : Object.entries(flatten(entry, path));
  })
);

test("shared operator messages provide matching English and German placeholders", () => {
  const german = flatten(sharedOperationsDe);
  const english = flatten(sharedOperationsEn);
  expect(Object.keys(english).sort()).toEqual(Object.keys(german).sort());
  const placeholders = (value) => [...value.matchAll(/{{\s*([^}]+)\s*}}/g)]
    .map((match) => match[1].trim()).sort();
  for (const [key, value] of Object.entries(german)) {
    expect(english[key].trim(), key).not.toBe("");
    expect(placeholders(english[key]), key).toEqual(placeholders(value));
  }
  expect(english["teamBalance.differenceWithLimit"]).toContain("Difference");
  expect(english["coordinatedSquadSwitch.name"]).toBe("Coordinated squad switch");
  expect(english["http.repeatedError"]).toContain("repeated");
});

test("shared operator UI no longer embeds German-only fallback messages", () => {
  const read = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), "utf8");
  const teamBalance = read("components/shared/TeamBalanceBar.jsx");
  expect(teamBalance).toContain('t("sharedOperations.teamBalance.differenceWithLimit"');
  expect(teamBalance).toContain('t("sharedOperations.teamBalance.distribution"');
  expect(teamBalance).not.toContain("Keine Live-Daten");
  const action = read("features/player-action/actions.js");
  expect(action).toContain('translationKey: "sharedOperations.coordinatedSquadSwitch"');
  const transport = read("utils/fetchUtils.js");
  expect(transport).toContain('i18n.t("sharedOperations.http.repeatedError"');
  expect(transport).toContain('i18n.t("sharedOperations.http.suppressedErrors"');
  expect(transport).not.toContain("wiederholt:");
  expect(read("components/PlayerProfileDrawer/index.jsx")).not.toContain("HH:MM");
  for (const path of [
    "components/VipDialog/PlayerVipSummary.js",
    "components/PlayersHistory/PlayerTile/PlayerSighthings.js",
    "components/PlayersHistory/PlayerTile/PlayerPenalties.js",
    "components/PlayerView/playerList.js",
  ]) {
    expect(read(path), path).toContain(".locale(");
    expect(read(path), path).toContain("useTranslation");
    expect(read(path), path).not.toContain("moment.locale(");
  }
});

test("records switch to English without a reload and remember the selection", async ({ page }) => {
  await page.setViewportSize(VIEWPORTS.desktop);
  const main = await openDemoPage(page, "/records/game-logs");
  await expect(main.getByRole("heading", { name: "Spielprotokolle", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Sprache", exact: true }).click();
  await page.getByRole("menuitem", { name: "English", exact: true }).click();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(main.getByRole("heading", { name: "Game logs", exact: true })).toBeVisible();
  await expect(main.getByText("Spielprotokolle", { exact: true })).toHaveCount(0);
  await expect.poll(() => page.evaluate(() => window.localStorage.getItem("crcon.language"))).toBe("en");
});
