import { ActionButton } from "@/features/player-action/ActionMenu";
import { Actions } from "@/features/player-action/actions";
import { alpha } from "@mui/material/styles";
import { Box } from "@mui/material";
import { useTranslation } from "react-i18next";

const stateButtonSx = (active, paletteKey = "primary") => ({
  minWidth: 0,
  height: 34,
  px: 0.75,
  overflow: "hidden",
  borderColor: (theme) =>
    active ? theme.palette[paletteKey].main : theme.palette.divider,
  bgcolor: (theme) =>
    active ? alpha(theme.palette[paletteKey].main, 0.12) : "transparent",
  color: (theme) =>
    active ? theme.palette[paletteKey].main : theme.palette.text.secondary,
  fontSize: "0.625rem",
  fontWeight: 600,
  letterSpacing: "0.04em",
  lineHeight: 1,
  whiteSpace: "nowrap",
  "& .MuiButton-startIcon": {
    mr: 0.5,
    "& svg": { fontSize: "1rem" },
  },
  "&:hover": {
    borderColor: (theme) => theme.palette[paletteKey].main,
    bgcolor: (theme) => alpha(theme.palette[paletteKey].main, 0.16),
  },
  "&:focus-visible": {
    outline: (theme) => `2px solid ${theme.palette.primary.main}`,
    outlineOffset: 1,
  },
});

function ActionList({ playerProfile }) {
  const { t } = useTranslation();
  const isWatched = playerProfile.is_watched;
  const isBlacklisted = playerProfile.is_blacklisted;
  const isBanned = playerProfile.is_banned;
  const isVip = playerProfile.is_vip;

  const statusActions = [
    {
      action: !isVip ? Actions.AddVIP : Actions.RemoveVIP,
      active: isVip,
      label: t("records.players.statusVip"),
      palette: "primary",
    },
    {
      action: !isWatched ? Actions.AddWatch : Actions.RemoveWatch,
      active: isWatched,
      label: t("records.players.statusWatched"),
      palette: "info",
    },
    {
      action: Actions.AddBlacklist,
      active: isBlacklisted,
      label: t("records.players.statusBlacklisted"),
      palette: "warning",
    },
    {
      action: !isBanned ? Actions.TempBan : Actions.RemoveBan,
      active: isBanned,
      label: t("records.players.statusBanned"),
      palette: "error",
    },
  ];

  return (
    <Box
      role="group"
      aria-label={t("records.players.statusActions")}
      sx={{
        display: "grid",
        gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
        gap: 0.5,
        width: "100%",
        "& > span": { display: "flex", minWidth: 0 },
        "& > span > .MuiButton-root": { width: "100%" },
      }}
    >
      {statusActions.map(({ action, active, label, palette }) => {
        const actionName = action.translationKey
          ? t(`${action.translationKey}.name`)
          : action.name;

        return (
          <ActionButton
            key={label}
            action={action}
            recipients={[playerProfile]}
            label={label}
            tooltipLabel={actionName}
            aria-pressed={active}
            sx={stateButtonSx(active, palette)}
          />
        );
      })}
    </Box>
  );
}

export default ActionList;
