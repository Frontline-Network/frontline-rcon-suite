import i18n from "./index";
import { automodActionReviewCopy } from "./locales/automod-action-review";

for (const [language, automodActionReview] of Object.entries(automodActionReviewCopy)) {
  i18n.addResourceBundle(language, "translation", { automodActionReview }, true, true);
}
