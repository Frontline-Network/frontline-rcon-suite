import * as React from "react";
import {
  ThemeProvider,
  createTheme,
  useColorScheme,
} from "@mui/material/styles";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTranslation } from "react-i18next";
import { loadThemeWithRetry } from "./load-theme.mjs";
import {
  applyAppearanceToThemeOptions,
  normalizeAppearance,
} from "./appearance";

function AppearanceModeSync({ appearance }) {
  const { setMode } = useColorScheme();

  React.useEffect(() => {
    setMode(appearance.mode);
    document.documentElement.dataset.colorVision = appearance.colorVision;
    document.documentElement.dataset.themePreset = appearance.preset;
    document.documentElement.dataset.wardogsStyle = appearance.wardogsStyle;
  }, [
    appearance.colorVision,
    appearance.mode,
    appearance.preset,
    appearance.wardogsStyle,
    setMode,
  ]);

  return null;
}

function AppTheme(props) {
  const { t } = useTranslation();
  const {
    children,
    disableCustomTheme,
    themeComponents,
    appearance: value,
  } = props;
  const [theme, setTheme] = React.useState(null);
  const [loadFailed, setLoadFailed] = React.useState(false);
  const systemDark = useMediaQuery("(prefers-color-scheme: dark)");
  const appearance = React.useMemo(() => normalizeAppearance(value), [value]);

  React.useEffect(() => {
    let active = true;
    setLoadFailed(false);
    async function initializeTheme() {
      if (disableCustomTheme) {
        if (active) setTheme({});
        return;
      }

      const defaultTheme = await loadThemeWithRetry(
        async () => {
          const module = await (appearance.preset === "wardogs"
            ? import("./wardogs/getWardogsTheme")
            : import("./default/getDefaultTheme"));
          return module.default(themeComponents);
        },
        () => active
      );
      if (!active) return;
      if (active) {
        setTheme(
          createTheme(
            applyAppearanceToThemeOptions(
              defaultTheme,
              appearance,
              appearance.preset === "wardogs" && !systemDark ? "light" : "dark"
            )
          )
        );
      }
    }

    initializeTheme().catch(() => {
      if (active) setLoadFailed(true);
    });
    return () => {
      active = false;
    };
  }, [appearance, disableCustomTheme, themeComponents, systemDark]);

  if (disableCustomTheme) {
    return <React.Fragment>{children}</React.Fragment>;
  }

  if (loadFailed || !theme) {
    return (
      <main
        style={{
          minHeight: "100dvh",
          display: "grid",
          placeItems: "center",
          background: "#121820",
          color: "#f4f6f8",
          fontFamily: "system-ui, sans-serif",
          padding: 24,
          boxSizing: "border-box",
        }}
      >
        <section
          role={loadFailed ? "alert" : "status"}
          style={{ maxWidth: 480 }}
        >
          <h1 style={{ fontSize: "1.35rem" }}>
            {t(loadFailed ? "themeLoading.failed" : "themeLoading.loading")}
          </h1>
          {loadFailed && (
            <>
              <p>{t("themeLoading.help")}</p>
              <button
                type="button"
                onClick={() => window.location.reload()}
                style={{
                  minHeight: 44,
                  padding: "10px 20px",
                  border: "1px solid #a4c9ff",
                  borderRadius: 4,
                  background: "#254a76",
                  color: "#fff",
                  cursor: "pointer",
                  font: "inherit",
                }}
              >
                {t("themeLoading.reload")}
              </button>
            </>
          )}
        </section>
      </main>
    );
  }

  return (
    <ThemeProvider
      theme={theme}
      defaultMode={appearance.mode}
      // The account store owns persistence. MUI's shared storage otherwise
      // broadcasts an unsaved preview to other tabs, which restore their own
      // mode and can continuously overwrite one another.
      storageManager={null}
      disableTransitionOnChange
    >
      <AppearanceModeSync appearance={appearance} />
      {children}
    </ThemeProvider>
  );
}

export default AppTheme;
