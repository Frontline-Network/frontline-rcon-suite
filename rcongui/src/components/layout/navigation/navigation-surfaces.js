import { alpha } from "@mui/material/styles";

const tintStrength = (theme, darkValue, lightValue) =>
  theme.palette.mode === "dark" ? darkValue : lightValue;

export const getCommandRailSurface = (theme) => ({
  backgroundColor: theme.palette.background.default,
  backgroundImage: `linear-gradient(180deg, ${alpha(
    theme.palette.primary.main,
    tintStrength(theme, 0.18, 0.11)
  )} 0%, ${alpha(
    theme.palette.primary.dark,
    tintStrength(theme, 0.09, 0.055)
  )} 48%, transparent 100%)`,
  boxShadow: `inset -1px 0 0 ${alpha(
    theme.palette.primary.main,
    tintStrength(theme, 0.16, 0.12)
  )}`,
});

export const getContextNavigationSurface = (theme) => ({
  backgroundColor: theme.palette.background.paper,
  backgroundImage: `linear-gradient(180deg, ${alpha(
    theme.palette.primary.main,
    tintStrength(theme, 0.1, 0.065)
  )} 0%, ${alpha(
    theme.palette.primary.main,
    tintStrength(theme, 0.035, 0.025)
  )} 38%, transparent 100%)`,
});

export const getNavigationControlSurface = (theme) =>
  alpha(theme.palette.primary.main, tintStrength(theme, 0.055, 0.04));
