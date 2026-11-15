import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";
import de from "./locales/de";
import en from "./locales/en";
import dayjs from "dayjs";
import "dayjs/locale/de";
import "dayjs/locale/fr";
import { dateLocale } from "./date-locale";
import LocalizedFormat from "dayjs/plugin/localizedFormat";

export const supportedLanguages = ["de", "en", "fr"];

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
    lng: initialLanguage === "fr" ? "en" : initialLanguage,
    fallbackLng: "en",
    load: "languageOnly",
    interpolation: { escapeValue: false },
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
      lookupLocalStorage: "crcon.language",
    },
  });

// French is deliberately a separate chunk: loading it in every session pushes
// the initial application bundle over its budget. Share in-flight loads so a
// rapid sequence of language selections never installs a partial catalog.
let frenchCatalogLoad;
let frenchCatalogLoaded = false;
export function ensureLanguageLoaded(language) {
  if (language !== "fr" || frenchCatalogLoaded) {
    return Promise.resolve();
  }
  if (!frenchCatalogLoad) {
    frenchCatalogLoad = import("./locales/fr").then(({ default: fr }) => {
      i18n.addResourceBundle("fr", "translation", fr, true, true);
      frenchCatalogLoaded = true;
    }).catch((error) => {
      frenchCatalogLoad = undefined;
      throw error;
    });
  }
  return frenchCatalogLoad;
}

let languageSelection = 0;
export async function selectAppLanguage(language) {
  const selection = ++languageSelection;
  await ensureLanguageLoaded(language);
  if (selection !== languageSelection) return false;
  await i18n.changeLanguage(language);
  return selection === languageSelection;
}

// Wait before mounting when French was saved, avoiding an English flash and
// ensuring document.lang, the picker locale and the visible text agree.
export const i18nReady = initialLanguage === "fr"
  ? ensureLanguageLoaded("fr").then(() => i18n.changeLanguage("fr"))
  : Promise.resolve();

const applyDocumentLanguage = (language) => {
  const locale = dateLocale(language);
  if (typeof document !== "undefined") document.documentElement.lang = locale;
  dayjs.locale(locale);
};
// The initial language is resolved before the event listener is registered.
// Keep assistive technology and date formatting correct on an English reload.
applyDocumentLanguage(i18n.resolvedLanguage || initialLanguage);
i18n.on("languageChanged", applyDocumentLanguage);

export default i18n;
