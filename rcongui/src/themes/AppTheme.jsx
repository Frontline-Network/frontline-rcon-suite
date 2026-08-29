import * as React from 'react';
import {
  ThemeProvider,
  createTheme,
  useColorScheme,
} from '@mui/material/styles';
import getDefaultTheme from './default/getDefaultTheme';
import {
  applyAppearanceToThemeOptions,
  normalizeAppearance,
} from './appearance';

function AppearanceModeSync({ appearance }) {
  const { setMode } = useColorScheme();

  React.useEffect(() => {
    setMode(appearance.mode);
    document.documentElement.dataset.colorVision = appearance.colorVision;
    document.documentElement.dataset.themePreset = appearance.preset;
  }, [appearance.colorVision, appearance.mode, appearance.preset, setMode]);

  return null;
}

function AppTheme(props) {
  const { children, disableCustomTheme, themeComponents, appearance: value } = props;
  const [theme, setTheme] = React.useState(null);
  const appearance = React.useMemo(() => normalizeAppearance(value), [value]);

  React.useEffect(() => {
    let active = true;
    async function initializeTheme() {
      if (disableCustomTheme) {
        if (active) setTheme({});
        return;
      }

      const defaultTheme = await getDefaultTheme(themeComponents, 'default');
      if (active) {
        setTheme(createTheme(applyAppearanceToThemeOptions(defaultTheme, appearance)));
      }
    }

    initializeTheme();
    return () => {
      active = false;
    };
  }, [appearance, disableCustomTheme, themeComponents]);

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
      colorSchemeStorageKey="fln.colorScheme"
      modeStorageKey="fln.colorMode"
      disableTransitionOnChange
    >
      <AppearanceModeSync appearance={appearance} />
      {children}
    </ThemeProvider>
  );
}

export default AppTheme;
