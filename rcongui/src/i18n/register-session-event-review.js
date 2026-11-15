import i18n from "./index";
import { sessionEventReviewCopy } from "./locales/session-event-review";

for (const [language, sessionEventReview] of Object.entries(sessionEventReviewCopy)) {
  i18n.addResourceBundle(language, "translation", { sessionEventReview }, true, true);
}
