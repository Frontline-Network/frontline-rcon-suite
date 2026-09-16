import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";
import de from "./locales/de";
import en from "./locales/en";
import dayjs from "dayjs";
import "dayjs/locale/de";
import LocalizedFormat from "dayjs/plugin/localizedFormat";

export const supportedLanguages = ["de", "en"];

dayjs.extend(LocalizedFormat);

const savedLanguage =
  typeof window !== "undefined"
    ? window.localStorage.getItem("crcon.language")
    : null;
const initialLanguage = supportedLanguages.includes(savedLanguage)
  ? savedLanguage
  : "de";

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      de: { translation: de },
      en: { translation: en },
    },
    supportedLngs: supportedLanguages,
    // German is the first-run language; an English string is shown only when
    // a German translation has not been supplied yet.
    lng: initialLanguage,
    fallbackLng: "en",
    load: "languageOnly",
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
      lookupLocalStorage: "crcon.language",
    },
  });

const applyDocumentLanguage = (language) => {
  const locale = language?.split("-")[0] === "en" ? "en" : "de";
  if (typeof document !== "undefined") document.documentElement.lang = locale;
  dayjs.locale(locale);
};
// The initial language is resolved before the event listener is registered.
// Keep assistive technology and date formatting correct on an English reload.
applyDocumentLanguage(i18n.resolvedLanguage || initialLanguage);
i18n.on("languageChanged", applyDocumentLanguage);

export default i18n;
