import i18n from "@/i18n";
import { barricadeScanReviewCopy } from "@/i18n/locales/barricade-scan-review";

for (const [language, value] of Object.entries(barricadeScanReviewCopy)) {
  i18n.addResourceBundle(language, "translation", { barricadeScanReview: value }, true, true);
}