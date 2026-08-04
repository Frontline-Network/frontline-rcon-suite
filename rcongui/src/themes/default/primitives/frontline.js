import { alpha, createTheme } from "@mui/material/styles";

const baseTheme = createTheme();

export const brand = {
  50: "#fff8e8",
  100: "#f5e4bd",
  200: "#f1cf83",
  300: "#d6b870",
  400: "#c59a4a",
  500: "#a77a37",
  600: "#7c5a2a",
  700: "#5f431f",
  800: "#352713",
  900: "#1c170d",
};

export const gray = {
  50: "#ede5d7",
  100: "#ded5c6",
  200: "#c5bca9",
  300: "#9d9788",
  400: "#77766b",
  500: "#595d54",
  600: "#3d433c",
  700: "#282e29",
  800: "#121611",
  900: "#080b08",
};

export const green = {
  50: "#effaf0",
  100: "#d7f0da",
  200: "#acdcb2",
  300: "#7dc788",
  400: "#62bd70",
  500: "#3e9650",
  600: "#2c713c",
  700: "#20552e",
  800: "#173b22",
  900: "#0d2515",
};

export const orange = {
  50: "#fff7e5",
  100: "#f9e4b4",
  200: "#efca7e",
  300: "#d9a950",
  400: "#bd8432",
  500: "#986526",
  600: "#76491f",
  700: "#593618",
  800: "#3b2512",
  900: "#24170c",
};

export const red = {
  50: "#fff1ee",
  100: "#f8d3cb",
  200: "#eaa59a",
  300: "#d77769",
  400: "#c55f51",
  500: "#a63f34",
  600: "#833027",
  700: "#62231d",
  800: "#431813",
  900: "#2a0e0b",
};

const palette = {
  primary: {
    light: brand[200],
    main: brand[400],
    dark: brand[600],
    contrastText: "#080b08",
  },
  secondary: {
    light: "#9fc2c5",
    main: "#6f9ea3",
    dark: "#466d72",
    contrastText: "#080b08",
  },
  info: {
    light: "#9fc2c5",
    main: "#6f9ea3",
    dark: "#466d72",
    contrastText: "#080b08",
  },
  success: {
    light: green[300],
    main: green[400],
    dark: green[700],
  },
  warning: {
    light: orange[300],
    main: orange[400],
    dark: orange[700],
  },
  error: {
    light: red[300],
    main: red[400],
    dark: red[700],
  },
  grey: gray,
  divider: alpha(brand[300], 0.2),
  background: {
    default: "#050706",
    paper: "#0a0d0a",
  },
  text: {
    primary: "#ede5d7",
    secondary: "#aaa493",
    disabled: "#696c63",
    red: red[300],
    orange: orange[300],
    green: green[300],
    blue: "#78aeb4",
  },
  action: {
    hover: alpha(brand[300], 0.08),
    selected: alpha(brand[400], 0.15),
    focus: alpha(brand[200], 0.2),
    disabled: alpha(gray[300], 0.38),
    disabledBackground: alpha(gray[700], 0.5),
  },
  baseShadow: "rgba(0, 0, 0, 0.5) 0 12px 32px",
};

export const colorSchemes = {
  light: { palette },
  dark: { palette },
};

export const typography = {
  fontFamily: 'Bahnschrift, "Segoe UI", system-ui, -apple-system, sans-serif',
  h1: {
    fontFamily: '"Bahnschrift Condensed", "Arial Narrow", Bahnschrift, sans-serif',
    fontSize: baseTheme.typography.pxToRem(48),
    fontWeight: 900,
    lineHeight: 1.08,
    letterSpacing: "0.015em",
  },
  h2: {
    fontFamily: '"Bahnschrift Condensed", "Arial Narrow", Bahnschrift, sans-serif',
    fontSize: baseTheme.typography.pxToRem(36),
    fontWeight: 900,
    lineHeight: 1.1,
    letterSpacing: "0.02em",
  },
  h3: {
    fontFamily: '"Bahnschrift Condensed", "Arial Narrow", Bahnschrift, sans-serif',
    fontSize: baseTheme.typography.pxToRem(30),
    fontWeight: 800,
    lineHeight: 1.15,
  },
  h4: {
    fontFamily: '"Bahnschrift Condensed", "Arial Narrow", Bahnschrift, sans-serif',
    fontSize: baseTheme.typography.pxToRem(24),
    fontWeight: 800,
    lineHeight: 1.2,
  },
  h5: {
    fontFamily: '"Bahnschrift Condensed", "Arial Narrow", Bahnschrift, sans-serif',
    fontSize: baseTheme.typography.pxToRem(20),
    fontWeight: 800,
  },
  h6: {
    fontFamily: '"Bahnschrift Condensed", "Arial Narrow", Bahnschrift, sans-serif',
    fontSize: baseTheme.typography.pxToRem(17),
    fontWeight: 800,
    letterSpacing: "0.06em",
    textTransform: "uppercase",
  },
  subtitle1: { fontSize: baseTheme.typography.pxToRem(16), fontWeight: 700 },
  subtitle2: { fontSize: baseTheme.typography.pxToRem(13), fontWeight: 700 },
  body1: { fontSize: baseTheme.typography.pxToRem(14) },
  body2: { fontSize: baseTheme.typography.pxToRem(13), fontWeight: 400 },
  caption: {
    fontSize: baseTheme.typography.pxToRem(11),
    fontWeight: 700,
    letterSpacing: "0.08em",
  },
  button: {
    fontWeight: 900,
    letterSpacing: "0.08em",
    textTransform: "uppercase",
  },
};

export const shape = { borderRadius: 8 };

export const shadows = [
  "none",
  "rgba(0, 0, 0, 0.28) 0 8px 24px",
  ...baseTheme.shadows.slice(2),
];
