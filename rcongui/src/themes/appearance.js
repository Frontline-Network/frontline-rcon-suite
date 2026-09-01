import { alpha, darken, getContrastRatio, lighten } from "@mui/material/styles";

export const APPEARANCE_VERSION = 1;

export const APPEARANCE_PRESETS = Object.freeze({
  "frontline-gold": {
    accent: "#c59a4a",
    dark: { background: "#050706", paper: "#0a0d0a" },
    light: { background: "#f6f4ef", paper: "#ffffff" },
  },
  "tactical-blue": {
    accent: "#5c9ed6",
    dark: { background: "#05080b", paper: "#0a1015" },
    light: { background: "#f2f6f9", paper: "#ffffff" },
  },
  "signal-green": {
    accent: "#56b978",
    dark: { background: "#050806", paper: "#09110c" },
    light: { background: "#f2f7f3", paper: "#ffffff" },
  },
  "command-red": {
    accent: "#d66d61",
    dark: { background: "#090606", paper: "#120b0a" },
    light: { background: "#faf3f2", paper: "#ffffff" },
  },
  neutral: {
    accent: "#a9aca8",
    dark: { background: "#070808", paper: "#0d0f0f" },
    light: { background: "#f4f5f4", paper: "#ffffff" },
  },
  custom: {
    accent: "#c59a4a",
    dark: { background: "#050706", paper: "#0a0d0a" },
    light: { background: "#f6f4ef", paper: "#ffffff" },
  },
});

export const COLOR_VISION_PALETTES = Object.freeze({
  standard: {
    info: "#6f9ea3",
    success: "#62bd70",
    warning: "#bd8432",
    error: "#c55f51",
  },
  deuteranopia: {
    info: "#56b4e9",
    success: "#0072b2",
    warning: "#e69f00",
    error: "#d55e00",
  },
  protanopia: {
    info: "#56b4e9",
    success: "#0072b2",
    warning: "#e69f00",
    error: "#cc79a7",
  },
  tritanopia: {
    info: "#cc79a7",
    success: "#009e73",
    warning: "#e69f00",
    error: "#d55e00",
  },
});

export const DEFAULT_APPEARANCE = Object.freeze({
  version: APPEARANCE_VERSION,
  mode: "dark",
  preset: "frontline-gold",
  customAccent: "#c59a4a",
  colorVision: "standard",
});

const MODES = new Set(["light", "dark", "system"]);
const COLOR_VISION_MODES = new Set(Object.keys(COLOR_VISION_PALETTES));
const HEX_COLOR = /^#[0-9a-f]{6}$/i;

export const isValidHexColor = (value) => HEX_COLOR.test(String(value || ""));

export function normalizeAppearance(value) {
  const source = value && typeof value === "object" ? value : {};
  const preset = Object.prototype.hasOwnProperty.call(
    APPEARANCE_PRESETS,
    source.preset
  )
    ? source.preset
    : DEFAULT_APPEARANCE.preset;
  const customAccent = isValidHexColor(source.customAccent)
    ? source.customAccent.toLowerCase()
    : APPEARANCE_PRESETS[preset].accent;

  return {
    version: APPEARANCE_VERSION,
    mode: MODES.has(source.mode) ? source.mode : DEFAULT_APPEARANCE.mode,
    preset,
    customAccent,
    colorVision: COLOR_VISION_MODES.has(source.colorVision)
      ? source.colorVision
      : DEFAULT_APPEARANCE.colorVision,
  };
}

export const appearancesEqual = (left, right) =>
  JSON.stringify(normalizeAppearance(left)) ===
  JSON.stringify(normalizeAppearance(right));

const contrastText = (color) =>
  getContrastRatio(color, "#080b08") >= 4.5 ? "#080b08" : "#ffffff";

export function makeAccessibleAccent(color, background, mode) {
  let candidate = isValidHexColor(color) ? color : DEFAULT_APPEARANCE.customAccent;
  let steps = 0;
  while (getContrastRatio(candidate, background) < 3 && steps < 8) {
    candidate = mode === "dark" ? lighten(candidate, 0.09) : darken(candidate, 0.09);
    steps += 1;
  }
  return candidate;
}

function semanticColor(main, mode) {
  return {
    light: mode === "dark" ? lighten(main, 0.18) : lighten(main, 0.08),
    main,
    dark: darken(main, mode === "dark" ? 0.22 : 0.16),
    contrastText: contrastText(main),
  };
}

function appearancePalette(mode, appearance) {
  const selected = APPEARANCE_PRESETS[appearance.preset];
  const surfaces = selected[mode];
  const requestedAccent =
    appearance.preset === "custom" ? appearance.customAccent : selected.accent;
  const accent = makeAccessibleAccent(requestedAccent, surfaces.background, mode);
  const semantic = COLOR_VISION_PALETTES[appearance.colorVision];
  const isDark = mode === "dark";

  return {
    mode,
    primary: {
      light: lighten(accent, 0.18),
      main: accent,
      dark: darken(accent, 0.22),
      contrastText: contrastText(accent),
    },
    secondary: semanticColor(semantic.info, mode),
    info: semanticColor(semantic.info, mode),
    success: semanticColor(semantic.success, mode),
    warning: semanticColor(semantic.warning, mode),
    error: semanticColor(semantic.error, mode),
    divider: alpha(accent, isDark ? 0.2 : 0.24),
    background: {
      default: surfaces.background,
      paper: surfaces.paper,
    },
    text: {
      primary: isDark ? "#ede5d7" : "#181b18",
      secondary: isDark ? "#aaa493" : "#565b56",
      disabled: isDark ? "#696c63" : "#858b85",
      red: semantic.error,
      orange: semantic.warning,
      green: semantic.success,
      blue: semantic.info,
    },
    action: {
      hover: alpha(accent, isDark ? 0.08 : 0.07),
      selected: alpha(accent, isDark ? 0.16 : 0.13),
      focus: alpha(accent, 0.24),
      disabled: alpha(isDark ? "#9d9788" : "#595d54", 0.38),
      disabledBackground: alpha(isDark ? "#282e29" : "#ded5c6", 0.5),
    },
    baseShadow: isDark
      ? "rgba(0, 0, 0, 0.5) 0 12px 32px"
      : "rgba(27, 34, 28, 0.16) 0 12px 32px",
  };
}

export function applyAppearanceToThemeOptions(baseOptions, value) {
  const appearance = normalizeAppearance(value);
  const defaultColorScheme = appearance.mode === "light" ? "light" : "dark";

  return {
    ...baseOptions,
    defaultColorScheme,
    colorSchemes: {
      light: { palette: appearancePalette("light", appearance) },
      dark: { palette: appearancePalette("dark", appearance) },
    },
    frontline: {
      ...baseOptions.frontline,
      appearance,
    },
  };
}
