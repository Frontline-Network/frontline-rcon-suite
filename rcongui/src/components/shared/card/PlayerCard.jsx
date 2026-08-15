import { generatePlayerActions } from "@/features/player-action/actions";
import {
  Card,
  CardContent,
  Stack,
  Divider,
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
        minWidth: 0,
        height: "100%",
        borderColor: (theme) => (selected ? theme.palette.primary.main : ""),
      }}
    >
      <CardContent sx={{ p: 1.5, "&:last-child": { pb: 1.5 } }}>
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
        <ActionList playerProfile={playerProfile} />
        <FlagList player={playerProfile} />
        <Stack
          direction="row"
          alignItems={"center"}
          justifyContent={"space-between"}
          spacing={2}
          sx={{ p: 1 }}
        >
          <div>
            <Typography variant="body2" color="text.secondary">
              {t("records.players.created")}
            </Typography>
            <Typography
              variant="caption"
              fontWeight={500}
              color="text.secondary"
            >
              {firstSeen}
            </Typography>
          </div>
          <div>
            <Typography variant="body2" color="text.secondary">
              {t("records.players.totalPlaytime")}
            </Typography>
            <Typography
              variant="caption"
              fontWeight={500}
              color="text.secondary"
            >
              {totalPlaytime} {t("records.players.hours")}
            </Typography>
          </div>
          <div>
            <Typography variant="body2" color="text.secondary">
              {t("records.players.lastSeen")}
            </Typography>
            <Typography
              variant="caption"
              fontWeight={500}
              color="text.secondary"
            >
              {lastSeen}
            </Typography>
          </div>
        </Stack>
        <Divider sx={{ my: 0 }} />
        <Stack
          direction="row"
          alignItems={"center"}
          justifyContent={"space-between"}
          spacing={2}
          sx={{ p: 1 }}
        >
          <Typography variant="caption" color="text.secondary">
            {t("actions.types.PUNISH")}:{" "}
            <Typography variant="caption" color="text.primary">
              {penalties?.PUNISH ?? 0}
            </Typography>
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t("actions.types.KICK")}:{" "}
            <Typography variant="caption" color="text.primary">
              {penalties?.KICK ?? 0}
            </Typography>
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t("actions.types.TEMPBAN")}:{" "}
            <Typography variant="caption" color="text.primary">
              {penalties?.TEMPBAN ?? 0}
            </Typography>
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t("actions.types.PERMABAN")}:{" "}
            <Typography variant="caption" color="text.primary">
              {penalties?.PERMABAN ?? 0}
            </Typography>
          </Typography>
        </Stack>
      </CardContent>
    </Card>
  );
}
