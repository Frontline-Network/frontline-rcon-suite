// French catalog with reviewed overrides; production rollout requires full validation.
import draft from "./fr-draft.json";
import { actionsFr } from "./fr-actions.js";
import { autobalancerFr } from "./fr-autobalancer.js";
import { frenchCore } from "./fr-core.js";
import { incidentsFr } from "./fr-incidents.js";
import { commonFr } from "./fr-common.js";
import { campaignsFr } from "./fr-campaigns.js";
import { navigationFr, sidebarFr } from "./fr-navigation.js";
import { mapsFr } from "./fr-maps.js";
import { accountInterfaceFr } from "./fr-account-interface.js";
import { remainingSettingsFr } from "./fr-settings-remaining.js";
import { otherSettingsFr } from "./fr-settings-others.js";
import { discordReportsFr } from "./fr-discord-reports.js";

const fr = {
  ...draft,
  ...frenchCore,
  ...accountInterfaceFr,
  common: commonFr,
  navigation: navigationFr,
  sidebar: sidebarFr,
  maps: mapsFr,
  actions: actionsFr,
  incidents: incidentsFr,
  language: { label: "Langue", de: "Deutsch", en: "English", fr: "Français", loadFailed: "La langue n’a pas pu être chargée. Veuillez réessayer." },
  settings: {
    ...draft.settings,
    ...remainingSettingsFr,
    others: otherSettingsFr,
    campaigns: campaignsFr,
    discordReports: discordReportsFr,
    configForms: {
      ...draft.settings.configForms,
      autobalancer: autobalancerFr,
    },
  },
};

export default fr;
