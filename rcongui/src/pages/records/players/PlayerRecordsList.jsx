import { memo, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  Avatar,
  Box,
  Checkbox,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
  useMediaQuery,
} from "@mui/material";
import dayjs from "dayjs";
import { useTranslation } from "react-i18next";
import { generatePlayerActions } from "@/features/player-action/actions";
import CopyableText from "@/components/shared/CopyableText";
import ProfileActions from "@/components/player/profile/Actions";
import PlatformChip from "@/components/player/profile/Platform";
import CountryChip from "@/components/player/profile/Country";
import LevelChip from "@/components/player/profile/Level";
import { OnlineStatusBadge } from "@/components/player/profile/styled";

const PlayerRecordsListRow = memo(function PlayerRecordsListRow({
  player,
  selected,
  onSelect,
}) {
  const { t, i18n } = useTranslation();
  const actionList = useMemo(
    () =>
      generatePlayerActions({
        multiAction: false,
        onlineAction: player.is_online,
      }),
    [player.is_online]
  );
  const name =
    player?.account?.name ??
    player.names?.[0]?.name ??
    player?.soldier?.name ??
    "???";
  const avatar = player?.steaminfo?.profile?.avatar ?? name;
  const penalties = player?.penalty_count ?? {};
  const lastSeen = dayjs(player.last_seen_timestamp_ms)
    .locale(i18n.language)
    .fromNow();
  const totalPlaytime = dayjs
    .duration((player.total_playtime_seconds ?? 0) * 1000)
    .asHours()
    .toFixed(1);
  const level = player?.level ?? player?.soldier?.level;
  const platform = player?.platform ?? player?.soldier?.platform;
  const country =
    player?.country ?? player?.account?.country ?? player?.steaminfo?.country;
  const linkedAccounts = player?.identity?.linked_accounts ?? [];

  return (
    <TableRow
      hover
      selected={selected}
      sx={{
        "& .MuiTableCell-root": { py: 1, verticalAlign: "middle" },
        "&.Mui-selected": {
          bgcolor: (theme) => `${theme.palette.primary.main}14`,
        },
      }}
    >
      <TableCell padding="checkbox">
        <Checkbox
          size="small"
          checked={selected}
          onChange={() => onSelect(player)}
          inputProps={{
            "aria-label": t("records.players.selectPlayer", { name }),
          }}
        />
      </TableCell>
      <TableCell>
        <Stack direction="row" spacing={1} alignItems="center" minWidth={240}>
          <OnlineStatusBadge
            overlap="circular"
            anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
            variant="dot"
            isOnline={player.is_online}
          >
            <Avatar src={avatar} sx={{ width: 38, height: 38 }}>
              {name[0]}
            </Avatar>
          </OnlineStatusBadge>
          <Box minWidth={0}>
            <Typography fontWeight={600} noWrap>
              <Link
                style={{ color: "inherit" }}
                to={`/records/players/${player.player_id}`}
              >
                {name}
              </Link>
            </Typography>
            <CopyableText
              text={player.player_id}
              size="0.7rem"
              sx={{ color: (theme) => theme.palette.text.secondary }}
            />
          </Box>
        </Stack>
      </TableCell>
      <TableCell>
        <Stack
          direction="row"
          spacing={0.5}
          alignItems="center"
          flexWrap="wrap"
          useFlexGap
        >
          <LevelChip
            level={level}
            playerId={player.player_id}
            currentSoldierData={player?.soldier}
          />
          <PlatformChip
            platform={platform}
            playerId={player.player_id}
            currentSoldierData={player?.soldier}
          />
          <CountryChip
            country={country}
            playerId={player.player_id}
            currentAccountData={player?.account}
          />
        </Stack>
      </TableCell>
      <TableCell>
        {linkedAccounts.length > 0 ? (
          <Stack spacing={0.25}>
            <Typography variant="body2" color="success.main">
              {t("records.players.linked")}
            </Typography>
            <Typography variant="caption" color="text.secondary" noWrap>
              {t("records.players.linkedCount", {
                count: linkedAccounts.length,
              })}
            </Typography>
          </Stack>
        ) : (
          <Typography color="text.secondary">—</Typography>
        )}
      </TableCell>
      <TableCell>
        <Typography variant="body2" noWrap>
          {lastSeen}
        </Typography>
      </TableCell>
      <TableCell>
        <Typography variant="body2" noWrap>
          {totalPlaytime} {t("records.players.hours")}
        </Typography>
      </TableCell>
      <TableCell>
        <Stack direction="row" spacing={1} alignItems="center">
          {[
            ["PUNISH", "P"],
            ["KICK", "K"],
            ["TEMPBAN", "T"],
            ["PERMABAN", "D"],
          ].map(([type, abbreviation]) => (
            <Tooltip key={type} title={t(`actions.types.${type}`)}>
              <Typography
                component="span"
                variant="caption"
                color={
                  (penalties[type] ?? 0) > 0 ? "text.primary" : "text.secondary"
                }
                whiteSpace="nowrap"
              >
                {abbreviation} {penalties[type] ?? 0}
              </Typography>
            </Tooltip>
          ))}
        </Stack>
      </TableCell>
      <TableCell align="right">
        <ProfileActions
          player={player}
          actions={actionList}
          aria-label={t("records.players.openPlayerActions", { name })}
          sx={{ width: 36, height: 36 }}
        />
      </TableCell>
    </TableRow>
  );
});

const MobilePlayerRecordsListRow = memo(function MobilePlayerRecordsListRow({
  player,
  selected,
  onSelect,
}) {
  const { t, i18n } = useTranslation();
  const actionList = useMemo(
    () =>
      generatePlayerActions({
        multiAction: false,
        onlineAction: player.is_online,
      }),
    [player.is_online]
  );
  const name =
    player?.account?.name ??
    player.names?.[0]?.name ??
    player?.soldier?.name ??
    "???";
  const avatar = player?.steaminfo?.profile?.avatar ?? name;
  const level = player?.level ?? player?.soldier?.level;
  const platform = player?.platform ?? player?.soldier?.platform;
  const lastSeen = dayjs(player.last_seen_timestamp_ms)
    .locale(i18n.language)
    .fromNow();
  const linkedCount = player?.identity?.linked_accounts?.length ?? 0;

  return (
    <Box
      component="li"
      sx={{
        alignItems: "center",
        bgcolor: selected ? "action.selected" : "transparent",
        borderBottom: (theme) => `1px solid ${theme.palette.divider}`,
        display: "grid",
        gridTemplateColumns: "44px 36px minmax(0, 1fr) 44px",
        minHeight: 72,
        px: 0.5,
        "&:last-child": { borderBottom: 0 },
      }}
    >
      <Checkbox
        size="small"
        checked={selected}
        onChange={() => onSelect(player)}
        inputProps={{
          "aria-label": t("records.players.selectPlayer", { name }),
        }}
        sx={{ minHeight: 44, minWidth: 44 }}
      />
      <OnlineStatusBadge
        overlap="circular"
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        variant="dot"
        isOnline={player.is_online}
      >
        <Avatar src={avatar} sx={{ width: 34, height: 34, fontSize: 14 }}>
          {name[0]}
        </Avatar>
      </OnlineStatusBadge>
      <Box
        component={Link}
        to={`/records/players/${player.player_id}`}
        sx={(theme) => ({
          color: "inherit",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          minHeight: 44,
          minWidth: 0,
          pl: 1,
          textDecoration: "none",
          "&:focus-visible": {
            outline: `2px solid ${theme.palette.primary.main}`,
            outlineOffset: 2,
          },
        })}
      >
        <Stack direction="row" spacing={0.75} alignItems="baseline">
          <Typography
            fontWeight={700}
            noWrap
            sx={{ color: "text.primary", minWidth: 0 }}
          >
            {name}
          </Typography>
          {linkedCount > 0 ? (
            <Typography
              variant="caption"
              color="success.main"
              sx={{ flex: "0 0 auto" }}
            >
              {t("records.players.linkedCount", { count: linkedCount })}
            </Typography>
          ) : null}
        </Stack>
        <Stack
          direction="row"
          spacing={0.75}
          alignItems="center"
          divider={<Box component="span" sx={{ color: "text.disabled" }}>·</Box>}
          sx={{ minWidth: 0, mt: 0.25 }}
        >
          <Typography variant="caption" color="text.secondary" noWrap>
            {t("views.table.level")} {level ?? "–"}
          </Typography>
          <Typography variant="caption" color="text.secondary" noWrap>
            {platform || t("common.unknown")}
          </Typography>
          <Typography
            variant="caption"
            color={player.is_online ? "success.main" : "text.secondary"}
            noWrap
            sx={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis" }}
          >
            {lastSeen}
          </Typography>
        </Stack>
      </Box>
      <ProfileActions
        player={player}
        actions={actionList}
        aria-label={t("records.players.openPlayerActions", { name })}
        sx={{ width: 44, height: 44 }}
      />
    </Box>
  );
});

export default function PlayerRecordsList({ players, selectedIds, onSelect }) {
  const { t } = useTranslation();
  const compact = useMediaQuery((theme) => theme.breakpoints.down("md"));

  if (compact) {
    return (
      <Box
        component="ul"
        aria-label={t("records.players.listLabel")}
        sx={{
          border: (theme) => `1px solid ${theme.palette.divider}`,
          bgcolor: "background.paper",
          listStyle: "none",
          m: 0,
          p: 0,
        }}
      >
        {players.map((player) => (
          <MobilePlayerRecordsListRow
            key={player.player_id}
            player={player}
            selected={selectedIds.has(player.player_id)}
            onSelect={onSelect}
          />
        ))}
      </Box>
    );
  }

  return (
    <TableContainer
      sx={{
        border: (theme) => `1px solid ${theme.palette.divider}`,
        borderRadius: 1,
        bgcolor: "background.paper",
      }}
    >
      <Table size="small" aria-label={t("records.players.listLabel")}>
        <TableHead>
          <TableRow>
            <TableCell padding="checkbox" />
            <TableCell>{t("records.players.player")}</TableCell>
            <TableCell>{t("records.players.platformLevel")}</TableCell>
            <TableCell>{t("records.players.accountLink")}</TableCell>
            <TableCell>{t("records.players.lastSeen")}</TableCell>
            <TableCell>{t("records.players.totalPlaytime")}</TableCell>
            <TableCell>{t("records.players.sanctions")}</TableCell>
            <TableCell align="right">{t("common.actions")}</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {players.map((player) => (
            <PlayerRecordsListRow
              key={player.player_id}
              player={player}
              selected={selectedIds.has(player.player_id)}
              onSelect={onSelect}
            />
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
