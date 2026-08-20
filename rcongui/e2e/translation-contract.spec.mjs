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
  "connectionStates.partial",
  "connectionStates.offline",
  "connectionStates.stale",
  "connectionStates.unknown",
  "connectionStates.disabled",
  "sidebar.gameServerState.partial",
  "sidebar.gameServerState.disabled",
  "sidebar.crconState.partial",
  "sidebar.crconState.disabled",
  "sidebar.gameServerState.stale",
  "sidebar.crconState.stale",
  "dashboard.lastUpdated",
  "dashboard.noLiveData",
  "dashboard.mapImageUnavailable",
  "dashboard.sections.operations",
  "dashboard.sections.moderation",
  "dashboard.sections.configuration",
  "dashboard.sections.analysis",
  "dashboard.sections.apps",
  "dashboard.resources.title",
  "dashboard.resources.subtitle",
  "dashboard.resources.states.ok",
  "dashboard.resources.states.warning",
  "dashboard.resources.states.critical",
  "dashboard.resources.states.partial",
  "dashboard.resources.states.stale",
  "dashboard.resources.states.unavailable",
  "dashboard.resources.messages.partial",
  "dashboard.resources.messages.stale",
  "dashboard.resources.messages.unavailable",
  "dashboard.resources.warningDetail",
  "dashboard.resources.history",
  "dashboard.resources.historySummary",
  "dashboard.resources.historySummaryMetric",
  "dashboard.resources.thresholds",
  "common.online",
  "common.offline",
  "common.unknown",
  "common.submit",
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
  "settings.discordReports.languageGerman",
  "settings.discordReports.languageEnglish",
  "settings.config.closeAutobalancerSettings",
  "settings.config.openAutobalancerSettings",
  "settings.config.basicMode",
  "settings.config.advancedJsonMode",
  "settings.config.reload",
  "settings.config.saveSettings",
  "settings.config.explanation",
  "settings.config.technicalSchema",
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
