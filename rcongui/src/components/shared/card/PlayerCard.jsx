import { generatePlayerActions } from "@/features/player-action/actions";
import {
  Box,
  Card,
  CardContent,
  Stack,
  Typography,
  Checkbox,
} from "@mui/material";
import dayjs from "dayjs";
import PlayerProfileHeader from "@/components/player/profile/Header";
import FlagList from "@/components/player/profile/FlagList";
import ActionList from "@/components/player/profile/ActionList";
import ProfileActions from "@/components/player/profile/Actions";
import { useMemo, useCallback } from "react";
import { useTranslation } from "react-i18next";
import LinkedAccounts from "@/components/player/profile/LinkedAccounts";

const ActivityMetric = ({ label, value, title }) => (
  <Box
    sx={{
      minWidth: 0,
      px: 1,
      py: 0.875,
      "&:not(:last-of-type)": {
        borderRight: (theme) => `1px solid ${theme.palette.divider}`,
      },
    }}
  >
    <Typography
      variant="caption"
      color="text.secondary"
      sx={{
        display: "block",
        mb: 0.25,
        fontSize: "0.65rem",
        letterSpacing: "0.06em",
        lineHeight: 1.25,
        textTransform: "uppercase",
      }}
    >
      {label}
    </Typography>
    <Typography
      variant="body2"
      color="text.primary"
      title={title ?? value}
      sx={{
        display: "-webkit-box",
        minHeight: "2.4em",
        overflow: "hidden",
        fontSize: "0.75rem",
        fontWeight: 500,
        lineHeight: 1.2,
        WebkitBoxOrient: "vertical",
        WebkitLineClamp: 2,
      }}
    >
      {value}
    </Typography>
  </Box>
);

const PenaltyMetric = ({ label, value, severe = false }) => (
  <Box
    sx={{
      minWidth: 0,
      px: 0.875,
      py: 0.75,
      "&:not(:last-of-type)": {
        borderRight: (theme) => `1px solid ${theme.palette.divider}`,
      },
    }}
  >
    <Typography
      variant="caption"
      color="text.secondary"
      noWrap
      sx={{ display: "block", fontSize: "0.625rem", lineHeight: 1.2 }}
    >
      {label}
    </Typography>
    <Typography
      variant="body2"
      color={
        value > 0 ? (severe ? "error.main" : "warning.main") : "text.disabled"
      }
      sx={{ mt: 0.25, fontWeight: 600, lineHeight: 1.2 }}
    >
      {value}
    </Typography>
  </Box>
);

export default function PlayerCard({
  player: playerProfile,
  onSelect,
  selected,
}) {
  const { t, i18n } = useTranslation();
  const name =
    playerProfile?.account?.name ??
    playerProfile.names?.[0]?.name ??
    playerProfile?.soldier?.name ??
    "???";
  const actionList = useMemo(
    () =>
      generatePlayerActions({
        multiAction: false,
        onlineAction: playerProfile.is_online,
      }),
    [playerProfile.is_online]
  );

  const handleSelect = useCallback(() => {
    onSelect(playerProfile);
  }, [onSelect, playerProfile]);

  const ActionListComponent = useCallback(
    () => (
      <Stack direction={"row"} spacing={0.25}>
        <Checkbox
          size="small"
          checked={selected}
          onChange={handleSelect}
          inputProps={{
            "aria-label": t("records.players.selectPlayer", { name }),
          }}
          sx={{ width: 24, height: 24 }}
        />
        <ProfileActions player={playerProfile} actions={actionList} />
      </Stack>
    ),
    [selected, handleSelect, playerProfile, actionList, name, t]
  );
  const avatar = playerProfile?.steaminfo?.profile?.avatar ?? name;
  const penalties = playerProfile?.penalty_count;
  const firstSeen = dayjs(playerProfile.first_seen_timestamp_ms)
    .locale(i18n.language)
    .format("L");
  const lastSeen = dayjs(playerProfile.last_seen_timestamp_ms).fromNow();
  const country =
    playerProfile?.country ??
    playerProfile?.account?.country ??
    playerProfile?.steaminfo?.country;
  const totalPlaytime = dayjs
    .duration(playerProfile.total_playtime_seconds * 1000)
    .asHours()
    .toFixed(1);
  const level = playerProfile?.level ?? playerProfile?.soldier?.level;
  const platform = playerProfile?.platform ?? playerProfile?.soldier?.platform;
  const clanTag = playerProfile?.clan_tag ?? playerProfile?.soldier?.clan_tag;

  return (
    <Card
      sx={{
        position: "relative",
        minWidth: 0,
        height: "100%",
        overflow: "hidden",
        borderColor: (theme) =>
          selected ? theme.palette.primary.main : theme.palette.divider,
        bgcolor: "background.paper",
        boxShadow: "none",
        transition: (theme) =>
          theme.transitions.create(["border-color", "background-color"], {
            duration: theme.transitions.duration.shortest,
          }),
        "&::before": {
          content: '""',
          position: "absolute",
          inset: "0 auto 0 0",
          width: 3,
          bgcolor: selected ? "primary.main" : "transparent",
        },
        "&:hover": {
          borderColor: (theme) => theme.palette.primary.dark,
          bgcolor: "action.hover",
        },
      }}
    >
      <CardContent
        sx={{
          display: "flex",
          flexDirection: "column",
          gap: 1,
          height: "100%",
          p: 1.5,
          "&:last-child": { pb: 1.5 },
        }}
      >
        <PlayerProfileHeader
          player={playerProfile}
          isOnline={playerProfile.is_online}
          ActionList={ActionListComponent}
          avatar={avatar}
          name={name}
          level={level}
          country={country}
          platform={platform}
          clanTag={clanTag}
        />
        <LinkedAccounts identity={playerProfile.identity} compact />

        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
          flexWrap="wrap"
          gap={0.5}
          sx={{
            minHeight: 36,
            mx: -1.5,
            px: 1.5,
            py: 0.375,
            borderTop: (theme) => `1px solid ${theme.palette.divider}`,
            borderBottom: (theme) => `1px solid ${theme.palette.divider}`,
            bgcolor: "action.hover",
          }}
        >
          <ActionList playerProfile={playerProfile} />
          <FlagList player={playerProfile} />
        </Stack>

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
            border: (theme) => `1px solid ${theme.palette.divider}`,
          }}
        >
          <ActivityMetric
            label={t("records.players.created")}
            value={firstSeen}
          />
          <ActivityMetric
            label={t("records.players.totalPlaytime")}
            value={`${totalPlaytime} ${t("records.players.hours")}`}
          />
          <ActivityMetric
            label={t("records.players.lastSeen")}
            value={lastSeen}
          />
        </Box>

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
            mt: "auto",
            border: (theme) => `1px solid ${theme.palette.divider}`,
            bgcolor: "background.default",
            "& > :nth-of-type(-n + 2)": {
              borderBottom: (theme) => `1px solid ${theme.palette.divider}`,
            },
            "& > :nth-of-type(2)": { borderRight: 0 },
          }}
        >
          <PenaltyMetric
            label={t("actions.types.PUNISH")}
            value={penalties?.PUNISH ?? 0}
          />
          <PenaltyMetric
            label={t("actions.types.KICK")}
            value={penalties?.KICK ?? 0}
          />
          <PenaltyMetric
            label={t("actions.types.TEMPBAN")}
            value={penalties?.TEMPBAN ?? 0}
            severe
          />
          <PenaltyMetric
            label={t("actions.types.PERMABAN")}
            value={penalties?.PERMABAN ?? 0}
            severe
          />
        </Box>
      </CardContent>
    </Card>
  );
}
