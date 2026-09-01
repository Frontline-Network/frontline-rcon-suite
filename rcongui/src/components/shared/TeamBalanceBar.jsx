import { Box, Stack, Typography } from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import { getThemeTeamColors } from "@/themes/teamColors";

const TeamBalanceBar = ({
  allies,
  axis,
  targetDifference,
  compact = false,
  alliesLabel = "Allies",
  axisLabel = "Axis",
}) => {
  const theme = useTheme();
  const teamColors = getThemeTeamColors(theme);
  const hasCounts = Number.isFinite(allies) && Number.isFinite(axis);
  const total = hasCounts ? allies + axis : 0;
  const alliesShare = total > 0 ? (allies / total) * 100 : 50;
  const difference = hasCounts ? Math.abs(allies - axis) : null;
  const withinTarget =
    difference !== null &&
    (targetDifference === undefined || difference <= targetDifference);
  const differenceLabel =
    difference === null
      ? "Keine Live-Daten"
      : targetDifference === undefined
      ? `Differenz ${difference}`
      : `Differenz ${difference} · erlaubt ${targetDifference}`;

  const teamSummary = (label, count, share, color, align) => (
    <Box
      sx={{
        minWidth: 0,
        flex: 1,
        p: compact ? 0.9 : 1.2,
        border: 1,
        borderColor: alpha(color, 0.68),
        bgcolor: alpha(color, 0.1),
        borderRadius: 1,
        textAlign: align,
      }}
    >
      <Typography
        variant="caption"
        sx={{
          color,
          fontWeight: 800,
          letterSpacing: 0.7,
          textTransform: "uppercase",
        }}
      >
        {label}
      </Typography>
      <Stack
        direction="row"
        justifyContent={align === "right" ? "flex-end" : "flex-start"}
        alignItems="baseline"
        spacing={0.75}
      >
        <Typography
          variant={compact ? "h6" : "h4"}
          sx={{
            fontWeight: 800,
            fontVariantNumeric: "tabular-nums",
            lineHeight: 1.1,
          }}
        >
          {count ?? "–"}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {hasCounts ? `${Math.round(share)} %` : "–"}
        </Typography>
      </Stack>
    </Box>
  );

  return (
    <Box
      aria-label={
        hasCounts
          ? `Teamverteilung: ${allies} ${alliesLabel} und ${axis} ${axisLabel}`
          : "Teamverteilung ist nicht verfügbar"
      }
      sx={{ mt: compact ? 1 : 1.5 }}
    >
      <Stack direction="row" spacing={compact ? 0.75 : 1}>
        {teamSummary(
          alliesLabel,
          allies,
          alliesShare,
          teamColors.allies,
          "left"
        )}
        {teamSummary(
          axisLabel,
          axis,
          100 - alliesShare,
          teamColors.axis,
          "right"
        )}
      </Stack>
      <Box
        sx={{
          position: "relative",
          height: compact ? 12 : 16,
          display: "flex",
          overflow: "hidden",
          borderRadius: 1,
          border: 1,
          borderColor: "divider",
          mt: compact ? 0.75 : 1,
          bgcolor: "background.paper",
        }}
      >
        <Box
          sx={{
            width: `${alliesShare}%`,
            minWidth: hasCounts && allies > 0 ? 3 : 0,
            bgcolor: teamColors.allies,
          }}
        />
        <Box sx={{ flexGrow: 1, bgcolor: teamColors.axis }} />
        <Box
          aria-hidden
          sx={{
            position: "absolute",
            top: 0,
            bottom: 0,
            left: `${alliesShare}%`,
            width: 2,
            transform: "translateX(-1px)",
            bgcolor: "common.white",
            boxShadow: "0 0 0 1px rgba(0, 0, 0, 0.38)",
          }}
        />
      </Box>
      <Typography
        variant="caption"
        sx={{
          display: "block",
          mt: 0.6,
          color: withinTarget
            ? "success.main"
            : difference === null
            ? "text.secondary"
            : "error.main",
          fontWeight: 700,
          textAlign: "center",
        }}
      >
        {differenceLabel}
      </Typography>
    </Box>
  );
};

export default TeamBalanceBar;
