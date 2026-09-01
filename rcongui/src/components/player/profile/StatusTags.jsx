import { Chip, Stack, Typography } from "@mui/material";
import StarIcon from "@mui/icons-material/Star";
import VisibilityIcon from "@mui/icons-material/Visibility";
import NoAccountsIcon from "@mui/icons-material/NoAccounts";
import GavelIcon from "@mui/icons-material/Gavel";
import { useTranslation } from "react-i18next";

const PlayerProfileStatusTags = ({
  isVip,
  isWatched,
  isBlacklisted,
  isBanned,
}) => {
  const { t } = useTranslation();
  const statuses = [
    isVip
      ? {
          key: "vip",
          label: t("records.playerDetails.statusVip"),
          icon: <StarIcon />,
          color: "primary",
        }
      : null,
    isWatched
      ? {
          key: "watched",
          label: t("records.playerDetails.statusWatched"),
          icon: <VisibilityIcon />,
          color: "warning",
        }
      : null,
    isBlacklisted
      ? {
          key: "blacklisted",
          label: t("records.playerDetails.statusBlacklisted"),
          icon: <NoAccountsIcon />,
          color: "error",
        }
      : null,
    isBanned
      ? {
          key: "banned",
          label: t("records.playerDetails.statusBanned"),
          icon: <GavelIcon />,
          color: "error",
        }
      : null,
  ].filter(Boolean);

  return (
    <Stack
      direction="row"
      alignItems="center"
      flexWrap="wrap"
      useFlexGap
      spacing={0.75}
      sx={{ py: 1 }}
    >
      {statuses.length ? (
        statuses.map((status) => (
          <Chip
            key={status.key}
            size="small"
            variant="outlined"
            color={status.color}
            icon={status.icon}
            label={status.label}
            sx={{ borderRadius: 0 }}
          />
        ))
      ) : (
        <Typography variant="body2" color="text.secondary">
          {t("records.playerDetails.noRiskStatus")}
        </Typography>
      )}
    </Stack>
  );
};

export default PlayerProfileStatusTags;
