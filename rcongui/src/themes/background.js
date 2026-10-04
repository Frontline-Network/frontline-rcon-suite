import { normalizeWardogsStyle } from "./wardogs/colorStyles";

const VANGUARD_BACKGROUNDS = {
  "frontline-gold": "amber",
  "tactical-blue": "blue",
  "signal-green": "emerald",
  "command-red": "rose",
  neutral: "slate",
  custom: "slate",
};

export function themeBackground(theme) {
  const appearance = theme.frontline.appearance;
  const style =
    appearance.preset === "wardogs"
      ? normalizeWardogsStyle(appearance.wardogsStyle)
      : VANGUARD_BACKGROUNDS[appearance.preset] || "slate";

  return {
    backgroundImage:
      theme.palette.mode === "dark"
        ? `url("/backgrounds/aurora-${style}.png")`
        : "none",
    backgroundSize: "100% auto",
    backgroundPosition: "center top",
    backgroundRepeat: "no-repeat",
    backgroundBlendMode: "lighten",
  };
}
