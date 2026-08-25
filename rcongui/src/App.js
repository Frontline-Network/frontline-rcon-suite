import { RouterProvider } from "react-router-dom";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import relativeTimePlugin from "dayjs/plugin/relativeTime";
import durationPlugin from "dayjs/plugin/duration";
import timezonePlugin from "dayjs/plugin/timezone";
import adminRouter from "./router";
import { QueryClientProvider } from "@tanstack/react-query";
import localforage from "localforage";
import siteConfig from "./config/siteConfig";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { queryClient } from "./queryClient";
import { StrictMode } from "react";
import AppTheme from "@/themes/AppTheme";
import { CssBaseline } from "@mui/material";
import { useAppStore } from "./stores/app-state";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { deDE, enUS } from "@mui/x-date-pickers/locales";
import { useTranslation } from "react-i18next";
import { useReleaseRefresh } from "./hooks/useReleaseRefresh";

const App = () => {
  useReleaseRefresh();
  const { i18n } = useTranslation();
  const isEnglish = i18n.resolvedLanguage === "en";
  const pickerLocale = isEnglish ? enUS : deDE;
  // Dayjs plugins
  dayjs.extend(relativeTimePlugin);
  dayjs.extend(durationPlugin);
  dayjs.extend(utc);
  dayjs.extend(timezonePlugin);

  // Configure LocalForage
  localforage.config({
    name: siteConfig.appName, // Name of the database
    storeName: "admin", // Name of the data store
    version: 1.0, // Database version
    description: "Local storage for Hell Let Loose CRCON web app", // Description for the database
    driver: [localforage.INDEXEDDB, localforage.LOCALSTORAGE], // Preferred storage drivers in order
  });

  const appearance = useAppStore(
    (state) => state.appearancePreview || state.appearance
  );

  return (
    <StrictMode>
      <QueryClientProvider client={queryClient}>
        <LocalizationProvider
          dateAdapter={AdapterDayjs}
          adapterLocale={isEnglish ? "en" : "de"}
          localeText={
            pickerLocale.components.MuiLocalizationProvider.defaultProps
              .localeText
          }
        >
          <AppTheme appearance={appearance}>
            <CssBaseline enableColorScheme />
            <RouterProvider router={adminRouter} />
            {import.meta.env.MODE !== "fake" ? (
              <ReactQueryDevtools initialIsOpen={false} />
            ) : null}
          </AppTheme>
        </LocalizationProvider>
      </QueryClientProvider>
    </StrictMode>
  );
};

export default App;
