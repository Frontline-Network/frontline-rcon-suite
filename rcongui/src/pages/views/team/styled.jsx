import { Box, styled } from "@mui/material";
import { getTierColors, getPlayerTier } from "@/utils/lib";

export const TeamContainer = styled(Box)(({ theme }) => ({
  display: "grid",
  gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
  gap: theme.spacing(1.5),
  alignItems: "start",
  minWidth: 0,
  paddingBottom: theme.spacing(10),
  [theme.breakpoints.down("lg")]: {
    gridTemplateColumns: "minmax(0, 1fr)",
  },
}));

export const LobbyContainer = styled(Box)(({ theme }) => ({
  marginBottom: theme.spacing(1.5),
  minWidth: 0,
}));

export const TeamBox = styled(Box, {
  shouldForwardProp: (prop) => prop !== "teamName",
})(({ theme, teamName }) => ({
  minWidth: 0,
  overflow: "hidden",
  border: `1px solid ${theme.palette.divider}`,
  borderRadius: theme.shape.borderRadius,
  backgroundColor: theme.palette.background.paper,
  boxShadow:
    teamName === "allies"
      ? "inset 0 2px 0 rgba(66,165,245,.45)"
      : teamName === "axis"
      ? "inset 0 2px 0 rgba(239,83,80,.45)"
      : "none",
}));

export const ScrollContainer = styled(Box)({
  minWidth: 0,
  overflowX: "clip",
});

export const ContentWrapper = styled(Box)({
  width: "100%",
  minWidth: 0,
});

const rowGrid = "44px minmax(150px, 1.35fr) minmax(130px, 1fr) 64px 72px";

const responsiveRow = (theme) => ({
  display: "grid",
  gridTemplateColumns: rowGrid,
  minWidth: 0,
  alignItems: "center",
  [theme.breakpoints.down("sm")]: {
    gridTemplateColumns: "44px minmax(0, 1fr) 64px",
    "& .leader-cell, & .level-cell": {
      display: "none",
    },
  },
});

export const HeaderRow = styled(Box)(({ theme }) => ({
  ...responsiveRow(theme),
  minHeight: 34,
  padding: theme.spacing(0, 1),
  borderTop: `1px solid ${theme.palette.divider}`,
  borderBottom: `1px solid ${theme.palette.divider}`,
  backgroundColor: theme.palette.background.default,
  color: theme.palette.text.secondary,
  "& > *": {
    padding: theme.spacing(0.5),
    minWidth: 0,
    fontSize: "0.7rem",
    fontWeight: 700,
    letterSpacing: ".04em",
    textTransform: "uppercase",
  },
  "& > :not(:nth-of-type(2))": { textAlign: "center" },
}));

export const TeamHeaderRow = styled(Box)(({ theme }) => ({
  minHeight: 58,
  display: "flex",
  alignItems: "center",
  gap: theme.spacing(1.25),
  padding: theme.spacing(1, 1.5),
  background:
    "linear-gradient(90deg, rgba(255,255,255,.035), rgba(255,255,255,0))",
  "& .team-title": {
    minWidth: 0,
    flex: 1,
  },
  "& .team-summary": {
    display: "flex",
    alignItems: "center",
    gap: theme.spacing(1.5),
    color: theme.palette.text.secondary,
    whiteSpace: "nowrap",
    [theme.breakpoints.down("sm")]: {
      gap: theme.spacing(0.75),
      "& .optional-summary": { display: "none" },
    },
  },
}));

export const SquadHeader = styled(Box, {
  shouldForwardProp: (prop) => prop !== "selected" && prop !== "hasProblem",
})(({ theme, selected, hasProblem }) => ({
  ...responsiveRow(theme),
  minHeight: 44,
  padding: theme.spacing(0, 1),
  borderBottom: `1px solid ${theme.palette.divider}`,
  backgroundColor: selected
    ? theme.palette.action.selected
    : theme.palette.background.paper,
  "&:hover": { backgroundColor: theme.palette.action.hover },
  "& .squad-main": {
    minWidth: 0,
    display: "flex",
    alignItems: "center",
    gap: theme.spacing(0.75),
  },
  "& .squad-name": {
    minWidth: 0,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    fontWeight: 800,
    textTransform: "uppercase",
  },
  "& .leader-cell": {
    minWidth: 0,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    color: hasProblem
      ? theme.palette.warning.main
      : theme.palette.text.secondary,
  },
  "& .level-cell, & .problem-cell": {
    textAlign: "center",
    whiteSpace: "nowrap",
    color: theme.palette.text.secondary,
  },
  "& .problem-cell": {
    color: hasProblem ? theme.palette.warning.main : theme.palette.success.main,
    fontWeight: 700,
  },
}));

export const PlayerRow = styled(Box, {
  shouldForwardProp: (prop) =>
    prop !== "selected" && prop !== "level" && prop !== "isCommander",
})(({ theme, selected, level, isCommander }) => ({
  ...responsiveRow(theme),
  minHeight: isCommander ? 52 : 44,
  padding: theme.spacing(0, 1),
  borderBottom: `1px solid ${theme.palette.divider}`,
  backgroundColor: selected
    ? theme.palette.action.selected
    : isCommander
    ? "rgba(255,255,255,.025)"
    : theme.palette.background.paper,
  "&:hover": { backgroundColor: theme.palette.action.hover },
  "& .player-info": {
    display: "flex",
    alignItems: "center",
    gap: theme.spacing(0.75),
    minWidth: 0,
  },
  "& .player-name": {
    minWidth: 0,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    color: selected ? theme.palette.primary.main : theme.palette.text.primary,
  },
  "& .leader-cell": {
    minWidth: 0,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    color: theme.palette.text.secondary,
  },
  "& .level-cell": {
    textAlign: "center",
    color: level
      ? getTierColors(theme.palette.mode)[getPlayerTier(level)]
      : theme.palette.text.secondary,
  },
  "& .problem-cell": {
    display: "flex",
    justifyContent: "center",
    gap: theme.spacing(0.75),
    color: theme.palette.text.secondary,
    whiteSpace: "nowrap",
  },
}));

export const CommanderRow = PlayerRow;

export const SquadGroupHeader = styled(Box)(({ theme }) => ({
  minHeight: 32,
  display: "flex",
  alignItems: "center",
  padding: theme.spacing(0.5, 1.5),
  borderBottom: `1px solid ${theme.palette.divider}`,
  backgroundColor: theme.palette.background.default,
  color: theme.palette.text.secondary,
  fontSize: "0.72rem",
  fontWeight: 800,
  letterSpacing: ".07em",
  textTransform: "uppercase",
}));
