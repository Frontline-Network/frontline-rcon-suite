import { alpha } from "@mui/material/styles";
import { normalizeWardogsStyle, WARDOGS_COLOR_STYLES } from "./colorStyles";

// A quiet, static backdrop matching the selected accent and sparse embers.
// Gradients stay sharp at every viewport size without a large image download.
export function wardogsBackground(mode, style) {
  const dark = mode === "dark";
  const colors = WARDOGS_COLOR_STYLES[normalizeWardogsStyle(style)];
  const embers = [
    [24, 76, 0.46], [46, 61, 0.5], [63, 175, 0.4],
    [73, 90, 0.48], [83, 142, 0.42], [54, 318, 0.4], [19, 217, 0.3],
  ];
  return {
    backgroundImage: [
      ...embers.map(([x, y, opacity]) =>
        `radial-gradient(circle at ${x}% ${y}px, ${alpha(colors.ember, dark ? opacity : opacity * 0.45)} 0 0.7px, transparent 1.4px)`
      ),
      `radial-gradient(ellipse 62vw 540px at 47% -70px, ${alpha(colors.glow, dark ? 0.27 : 0.045)} 0%, transparent 82%)`,
      `radial-gradient(ellipse 42vw 360px at 69% 35px, ${alpha(colors.glowSecondary, dark ? 0.1 : 0.025)} 0%, transparent 90%)`,
    ].join(", "),
    backgroundRepeat: "no-repeat",
    backgroundAttachment: "fixed",
  };
}
