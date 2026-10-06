import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = (path) => readFileSync(new URL(path, import.meta.url), "utf8");
const { copy } = await import(
  `data:text/javascript;base64,${Buffer.from(source("./copy.js")).toString(
    "base64"
  )}`
);

test("report admin is in the AI wizard, not below it or behind a leadership vote", () => {
  const wizard = source("../general-group/crcon-app/DiscordReportBotCard.jsx");
  const page = source("../../apps/discord-report-bot/index.jsx");
  assert.match(wizard, /<ReportAdmin embedded\s*\/>/);
  assert.ok(
    wizard.indexOf("<ReportAdmin embedded") <
      wizard.indexOf("settings.discordReports.sectionAiHelp")
  );
  assert.doesNotMatch(page, /LeadershipVotes|<ReportAdmin/);
});

test("German and English explain real kicks separately from manual cheat assessment", () => {
  assert.deepEqual(Object.keys(copy.de).sort(), Object.keys(copy.en).sort());
  assert.match(copy.en.teamkills, /60-second/);
  assert.match(copy.de.teamkills, /60 Sekunden/);
  assert.match(copy.en.cheating, /No automatic cheat kicks or bans/);
  assert.match(copy.de.cheating, /Keine automatischen Cheat-Kicks oder Banns/);
  assert.match(copy.en.info, /without an AI account/);
  assert.match(copy.en.save, /report rules/);
  for (const language of [copy.de, copy.en]) {
    for (const value of Object.values(language)) assert.ok(value.trim());
  }
});

test("new cheat review switch shares existing permission-gated, server-local save", () => {
  const page = source("./index.jsx");
  assert.match(page, /\["cheating", c.cheatToggle\]/);
  assert.match(page, /window.location.origin, user\?\.username/);
  assert.match(page, /can_manage_discord_report_bot/);
  assert.match(page, /fetchWithCsrf/);
});
