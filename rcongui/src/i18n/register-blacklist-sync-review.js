import i18n from "@/i18n";
import { blacklistSyncReviewCopy } from "@/i18n/locales/blacklist-sync-review";

for (const [language, copy] of Object.entries(blacklistSyncReviewCopy)) {
  i18n.addResourceBundle(language, "translation", { blacklistSyncReview: copy }, true, true);
}
