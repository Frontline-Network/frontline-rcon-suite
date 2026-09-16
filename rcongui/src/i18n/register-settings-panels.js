import i18n from "./index";
import { settingsPanelsDe, settingsPanelsEn } from "./locales/settings-panels.js";

// Loaded by the lazy settings/incident components before they render. Keep the
// long operator guides out of the startup bundle without asynchronous fallbacks.
for (const [language, settingsPanels] of Object.entries({
  de: settingsPanelsDe,
  en: settingsPanelsEn,
})) {
  i18n.addResourceBundle(language, "translation", { settingsPanels }, true, true);
}
