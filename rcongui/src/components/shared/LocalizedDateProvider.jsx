import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { deDE, enUS, frFR } from "@mui/x-date-pickers/locales";
import { useTranslation } from "react-i18next";
import { dateLocale } from "@/i18n/date-locale";

// Nested picker providers must follow the selected UI language too. Relying
// on a global date-library locale can keep a cached adapter in the old language.
export default function LocalizedDateProvider({ children, localeText, ...props }) {
  const { i18n } = useTranslation();
  const language = dateLocale(i18n.resolvedLanguage);
  const translations = { de: deDE, en: enUS, fr: frFR }[language];

  return (
    <LocalizationProvider
      dateAdapter={AdapterDayjs}
      {...props}
      adapterLocale={language}
      localeText={{
        ...translations.components.MuiLocalizationProvider.defaultProps.localeText,
        ...localeText,
      }}
    >
      {children}
    </LocalizationProvider>
  );
}
