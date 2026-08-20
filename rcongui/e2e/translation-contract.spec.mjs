import { expect, test } from "@playwright/test";
import de from "../src/i18n/locales/de.js";
import en from "../src/i18n/locales/en.js";

// Playwright's transform can retain an additional default-export wrapper for
// typeless .js modules while native Node imports do not. Validate the actual
// locale object in both environments.
const germanResources = de?.default ?? de;
const englishResources = en?.default ?? en;

const getPath = (source, path) =>
  path.split(".").reduce((value, key) => value?.[key], source);

const criticalTranslationKeys = [
  "common.skipToContent",
  "common.toggleContentWidth",
  "navigation.primary",
  "navigation.openMenu",
  "navigation.toggleMenu",
  "navigation.search",
  "navigation.permissionMissing",
  "navigation.groups.views",
  "navigation.groups.liveOperations",
  "navigation.groups.playersModeration",
  "navigation.groups.mapsGameOperations",
  "navigation.groups.automation",
  "navigation.groups.integrations",
  "navigation.groups.serverConfiguration",
  "navigation.groups.logsAnalytics",
  "navigation.groups.systemDiagnostics",
  "sidebar.selectServer",
  "sidebar.serverNumber",
  "sidebar.gameServerConnected",
  "sidebar.gameServerOffline",
  "sidebar.gameServerUnknown",
  "sidebar.crconOffline",
  "connectionStates.loading",
  "connectionStates.online",
  "connectionStates.offline",
  "connectionStates.stale",
  "connectionStates.unknown",
  "sidebar.gameServerState.stale",
  "sidebar.crconState.stale",
  "dashboard.lastUpdated",
  "dashboard.noLiveData",
  "dashboard.mapImageUnavailable",
  "common.online",
  "common.offline",
  "common.unknown",
  "errors.title",
  "errors.requestFailed",
  "actions.missingPermission",
  "actions.context.connectionBlocked",
  "actions.disband.permissionMissing",
  "actions.disband.review",
  "actions.disband.execute",
  "actions.disband.retryFailed",
  "actions.disband.openAudit",
  "settings.discordReports.title",
  "settings.discordReports.subtitle",
  "settingEffect.serverValue",
  "settingEffect.draftValue",
  "settingEffect.recommendedValue",
  "settingEffect.unverified",
  "settingEffect.commandSent",
  "settingEffect.notDocumented",
  "settingEffect.permissionMissing",
  "settingEffect.discardDraft",
  "settingEffect.conflicts.autoSettings",
  "settingEffect.conflicts.vipAutomation",
  "settingEffect.conflicts.autobalancer",
  "settingEffect.conflicts.autoVotekick",
  "serverSettings.loading",
  "serverSettings.unavailable",
  "serverSettings.lastRead",
];

test("critical QA and state labels exist in German and English", () => {
  for (const key of criticalTranslationKeys) {
    const german = getPath(germanResources, key);
    const english = getPath(englishResources, key);

    expect(german, `missing German translation: ${key}`).toEqual(
      expect.any(String)
    );
    expect(english, `missing English translation: ${key}`).toEqual(
      expect.any(String)
    );
    expect(german.trim(), `empty German translation: ${key}`).not.toBe("");
    expect(english.trim(), `empty English translation: ${key}`).not.toBe("");
  }
});
