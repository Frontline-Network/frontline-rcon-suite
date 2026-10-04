import { useEffect, useState } from "react";
import { Box, Button } from "@mui/material";
import { alpha } from "@mui/material/styles";
import PauseRoundedIcon from "@mui/icons-material/PauseRounded";
import PlayArrowRoundedIcon from "@mui/icons-material/PlayArrowRounded";
import { useTranslation } from "react-i18next";
import { useBackgroundMotion } from "@/hooks/useBackgroundMotion";
import {
  WARDOGS_COLOR_STYLES,
  normalizeWardogsStyle,
} from "@/themes/wardogs/colorStyles";

// Fixed positions and negative delays keep movement continuous across renders.
const SPARKS = [
  [9, 52, -19, 14],
  [17, 64, -49, -18],
  [28, 58, -10, 20],
  [39, 72, -41, -12],
  [51, 61, -54, 16],
  [64, 68, -24, -22],
  [77, 55, -37, 12],
  [89, 74, -58, -16],
  [97, 63, -31, 18],
];

export function BackgroundMotionButton() {
  const { t } = useTranslation();
  const { playing, reduced, toggle } = useBackgroundMotion();
  return (
    <Button
      size="small"
      variant="text"
      disabled={reduced}
      onClick={toggle}
      startIcon={playing ? <PauseRoundedIcon /> : <PlayArrowRoundedIcon />}
      sx={{ color: "text.secondary", minHeight: 40 }}
    >
      {t(
        reduced
          ? "appearance.motion.reduced"
          : playing
          ? "appearance.motion.pause"
          : "appearance.motion.play"
      )}
    </Button>
  );
}

export default function AmbientBackground() {
  const { playing } = useBackgroundMotion();
  const [visible, setVisible] = useState(() => !document.hidden);
  useEffect(() => {
    const update = () => setVisible(!document.hidden);
    document.addEventListener("visibilitychange", update);
    return () => document.removeEventListener("visibilitychange", update);
  }, []);
  const active = playing && visible;
  return (
    <Box
      aria-hidden="true"
      data-testid="ambient-background"
      data-motion={active ? "playing" : "paused"}
      sx={(theme) => {
        const dark = theme.palette.mode === "dark";
        const aurora = theme.frontline.appearance.preset === "wardogs";
        const colors = aurora
          ? WARDOGS_COLOR_STYLES[
              normalizeWardogsStyle(theme.frontline.appearance.wardogsStyle)
            ]
          : {
              glow: theme.palette.primary.main,
              glowSecondary: theme.palette.primary.dark,
              ember: theme.palette.primary.light,
            };
        return {
          position: "fixed",
          inset: 0,
          zIndex: -1,
          pointerEvents: "none",
          overflow: "hidden",
          "& > *": {
            animationPlayState: active ? "running" : "paused",
            willChange: active ? "transform" : "auto",
          },
          "& .ambient-glow": {
            position: "absolute",
            inset: "-4%",
            height: "min(900px, 110vh)",
            backgroundRepeat: "no-repeat",
            backgroundImage: `radial-gradient(ellipse 58% 65% at 48% 0%, ${alpha(
              colors.glow,
              dark ? (aurora ? 0.28 : 0.09) : 0.055
            )}, transparent 85%), radial-gradient(ellipse 38% 50% at 82% 15%, ${alpha(
              colors.glowSecondary,
              dark ? 0.14 : 0.03
            )}, transparent 85%)`,
            animationName: "crcon-ambient-drift",
            animationDuration: "44s",
            animationTimingFunction: "ease-in-out",
            animationIterationCount: "infinite",
            animationDirection: "alternate",
          },
          "& .ambient-spark": {
            position: "absolute",
            bottom: -8,
            width: "1.5px",
            borderRadius: "50%",
            bgcolor: alpha(colors.ember, dark ? 0.8 : 0.45),
            boxShadow: `0 0 5px ${alpha(colors.ember, 0.3)}`,
            opacity: 0,
            animationName: "crcon-spark-rise",
            animationTimingFunction: "linear",
            animationIterationCount: "infinite",
          },
          "@keyframes crcon-ambient-drift": {
            from: { transform: "translate3d(-2%, -1%, 0) scale(1)" },
            to: { transform: "translate3d(3%, 3%, 0) scale(1.06)" },
          },
          "@keyframes crcon-spark-rise": {
            "0%": { transform: "translate3d(0, 0, 0)", opacity: 0 },
            "15%": { opacity: 0.45 },
            "65%": { opacity: 0.35 },
            "100%": {
              transform: "translate3d(var(--spark-drift), -105vh, 0)",
              opacity: 0,
            },
          },
          "@media (prefers-reduced-motion: reduce)": {
            "& > *": { animation: "none", willChange: "auto" },
          },
          "@media print": { display: "none" },
        };
      }}
    >
      <div className="ambient-glow" />
      {SPARKS.map(([left, duration, delay, drift], index) => (
        <span
          key={left}
          className="ambient-spark"
          style={{
            left: `${left}%`,
            animationDuration: `${duration}s`,
            animationDelay: `${delay}s`,
            "--spark-drift": `${drift}px`,
            height: index % 3 === 0 ? "4px" : "2px",
          }}
        />
      ))}
    </Box>
  );
}
