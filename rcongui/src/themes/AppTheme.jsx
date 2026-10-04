import * as React from "react";
import {
  ThemeProvider,
  createTheme,
  useColorScheme,
} from "@mui/material/styles";
import useMediaQuery from "@mui/material/useMediaQuery";
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
  }, [appearance.colorVision, appearance.mode, appearance.preset, appearance.wardogsStyle, setMode]);

  return null;
}

function AppTheme(props) {
  const {
    children,
    disableCustomTheme,
    themeComponents,
    appearance: value,
  } = props;
  const [theme, setTheme] = React.useState(null);
  const systemDark = useMediaQuery("(prefers-color-scheme: dark)");
  const appearance = React.useMemo(() => normalizeAppearance(value), [value]);

  React.useEffect(() => {
    let active = true;
    async function initializeTheme() {
      if (disableCustomTheme) {
        if (active) setTheme({});
        return;
      }

      const getTheme =
        appearance.preset === "wardogs"
          ? (await import("./wardogs/getWardogsTheme")).default
          : (await import("./default/getDefaultTheme")).default;
      const defaultTheme = await getTheme(themeComponents);
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

    initializeTheme();
    return () => {
      active = false;
    };
  }, [appearance, disableCustomTheme, themeComponents, systemDark]);

  if (disableCustomTheme) {
    return <React.Fragment>{children}</React.Fragment>;
  }

  if (!theme) {
    return null; // Or a loading indicator
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
