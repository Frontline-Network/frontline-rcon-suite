import i18n from "./index";
import { seedVipJournalCopy } from "./locales/seed-vip-journal";

for (const [language, seedVipJournal] of Object.entries(seedVipJournalCopy)) {
  i18n.addResourceBundle(language, "translation", { seedVipJournal }, true, true);
}
