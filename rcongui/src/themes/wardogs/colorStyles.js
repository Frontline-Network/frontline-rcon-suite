// Keep the accent pairs aligned with api/wardogs_styles.py (contract tested).
export const WARDOGS_COLOR_STYLES = Object.freeze({
  rose: { accent: "#e45b80", lightAccent: "#b72d58", glow: "#700e17", glowSecondary: "#550c15", ember: "#de3d4d" },
  blue: { accent: "#61a9ee", lightAccent: "#2368a6", glow: "#143e70", glowSecondary: "#102e52", ember: "#61a9ee" },
  emerald: { accent: "#51bb99", lightAccent: "#187553", glow: "#0e513c", glowSecondary: "#0b392f", ember: "#51bb99" },
  amber: { accent: "#dda44e", lightAccent: "#875d12", glow: "#68400f", glowSecondary: "#4b3010", ember: "#dda44e" },
  violet: { accent: "#b393f1", lightAccent: "#7045b4", glow: "#47226e", glowSecondary: "#34184f", ember: "#b393f1" },
  slate: { accent: "#adb9cc", lightAccent: "#56667d", glow: "#39475b", glowSecondary: "#273345", ember: "#adb9cc" },
});

export const DEFAULT_WARDOGS_STYLE = "rose";
export const normalizeWardogsStyle = (value) =>
  typeof value === "string" && Object.prototype.hasOwnProperty.call(WARDOGS_COLOR_STYLES, value)
    ? value
    : DEFAULT_WARDOGS_STYLE;
