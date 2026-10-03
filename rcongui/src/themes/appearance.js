import { alpha, darken, getContrastRatio, lighten } from "@mui/material/styles";
import { DEFAULT_WARDOGS_STYLE, normalizeWardogsStyle, WARDOGS_COLOR_STYLES } from "./wardogs/colorStyles";
import {
  DEFAULT_WARDOGS_SHORTCUTS,
  normalizeWardogsShortcuts,
} from "../components/layout/navigation/wardogs-shortcuts.mjs";

export const APPEARANCE_VERSION = 1;

export const APPEARANCE_PRESETS = Object.freeze({
  "frontline-gold": {
    accent: "#c59a4a",
    dark: { background: "#050706", paper: "#0a0d0a" },
    light: { background: "#f6f4ef", paper: "#ffffff" },
  },
  wardogs: {
    accent: "#e45b80",
    dark: { background: "#0d0d0f", paper: "#141416" },
    light: { background: "#f5f5f7", paper: "#ffffff" },
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
  wardogsStyle: DEFAULT_WARDOGS_STYLE,
  wardogsShortcuts: DEFAULT_WARDOGS_SHORTCUTS,
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
    wardogsStyle: normalizeWardogsStyle(source.wardogsStyle),
    colorVision: COLOR_VISION_MODES.has(source.colorVision)
      ? source.colorVision
      : DEFAULT_APPEARANCE.colorVision,
    wardogsShortcuts: normalizeWardogsShortcuts(source.wardogsShortcuts),
  };
}

export const appearancesEqual = (left, right) =>
  JSON.stringify(normalizeAppearance(left)) ===
  JSON.stringify(normalizeAppearance(right));

const contrastText = (color) =>
  getContrastRatio(color, "#080b08") >= 4.5 ? "#080b08" : "#ffffff";

export function makeAccessibleAccent(
  color,
  background,
  mode,
  minimumContrast = 3
) {
  let candidate = isValidHexColor(color)
    ? color
    : DEFAULT_APPEARANCE.customAccent;
  let steps = 0;
  while (
    getContrastRatio(candidate, background) < minimumContrast &&
    steps < 8
  ) {
    candidate =
      mode === "dark" ? lighten(candidate, 0.09) : darken(candidate, 0.09);
    steps += 1;
  }
  return candidate;
}

function semanticColor(main, mode, accessible = false) {
  return {
    light:
      mode === "dark"
        ? lighten(main, 0.18)
        : accessible
        ? darken(main, 0.08)
        : lighten(main, 0.08),
    main,
    dark: darken(main, mode === "dark" ? 0.22 : 0.16),
    contrastText: contrastText(main),
  };
}

function appearancePalette(mode, appearance) {
  const selected = APPEARANCE_PRESETS[appearance.preset];
  const surfaces = selected[mode];
  const isWardogs = appearance.preset === "wardogs";
  const wardogsStyle = WARDOGS_COLOR_STYLES[appearance.wardogsStyle];
  const requestedAccent = isWardogs
    ? wardogsStyle[mode === "light" ? "lightAccent" : "accent"]
    : appearance.preset === "custom" ? appearance.customAccent : selected.accent;
  const accent = makeAccessibleAccent(
    requestedAccent,
    surfaces.background,
    mode,
    isWardogs ? 4.5 : 3
  );
  const semantic = Object.fromEntries(
    Object.entries(COLOR_VISION_PALETTES[appearance.colorVision]).map(
      ([key, color]) => [
        key,
        isWardogs
          ? makeAccessibleAccent(color, surfaces.paper, mode, 4.5)
          : color,
      ]
    )
  );
  const isDark = mode === "dark";

  return {
    mode,
    primary: {
      light: isWardogs && !isDark ? darken(accent, 0.1) : lighten(accent, 0.18),
      main: accent,
      dark: darken(accent, 0.22),
      contrastText: contrastText(accent),
    },
    secondary: semanticColor(semantic.info, mode, isWardogs),
    info: semanticColor(semantic.info, mode, isWardogs),
    success: semanticColor(semantic.success, mode, isWardogs),
    warning: semanticColor(semantic.warning, mode, isWardogs),
    error: semanticColor(semantic.error, mode, isWardogs),
    divider: isWardogs
      ? isDark
        ? "#2b2b31"
        : "#d9d9e0"
      : alpha(accent, isDark ? 0.2 : 0.24),
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
      ...(isWardogs && {
        primary: isDark ? "#ededf0" : "#202027",
        secondary: isDark ? "#aaa8b3" : "#62616e",
        disabled: isDark ? "#767480" : "#8b8995",
      }),
    },
    action: {
      hover: alpha(accent, isDark ? 0.08 : 0.07),
      selected: alpha(accent, isDark ? 0.16 : 0.13),
      focus: alpha(accent, 0.24),
      disabled: alpha(isDark ? "#9d9788" : "#595d54", 0.38),
      disabledBackground: alpha(isDark ? "#282e29" : "#ded5c6", 0.5),
      ...(isWardogs && {
        disabled: alpha(isDark ? "#aaa8b3" : "#62616e", 0.38),
        disabledBackground: alpha(isDark ? "#303036" : "#e7e7eb", 0.5),
      }),
    },
    baseShadow: isDark
      ? "rgba(0, 0, 0, 0.5) 0 12px 32px"
      : "rgba(27, 34, 28, 0.16) 0 12px 32px",
  };
}

export function applyAppearanceToThemeOptions(
  baseOptions,
  value,
  systemMode = "dark"
) {
  const appearance = normalizeAppearance(value);
  const defaultColorScheme =
    appearance.mode === "system" ? systemMode : appearance.mode;

  return {
    ...baseOptions,
    defaultColorScheme,
    colorSchemes: {
      light: {
        palette: {
          ...(appearance.preset === "wardogs" &&
            baseOptions.colorSchemes?.light?.palette),
          ...appearancePalette("light", appearance),
        },
      },
      dark: {
        palette: {
          ...(appearance.preset === "wardogs" &&
            baseOptions.colorSchemes?.dark?.palette),
          ...appearancePalette("dark", appearance),
        },
      },
    },
    frontline: {
      ...baseOptions.frontline,
      appearance,
    },
  };
}
