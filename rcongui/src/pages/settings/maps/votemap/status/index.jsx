import { useEffect, useMemo, useState } from "react";
import { useLoaderData } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  IconButton,
  LinearProgress,
  Pagination,
  Popover,
  Stack,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import AnnouncementOutlinedIcon from "@mui/icons-material/AnnouncementOutlined";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import CloseIcon from "@mui/icons-material/Close";
import EmojiEventsOutlinedIcon from "@mui/icons-material/EmojiEventsOutlined";
import HowToVoteOutlinedIcon from "@mui/icons-material/HowToVoteOutlined";
import PowerIcon from "@mui/icons-material/Power";
import PowerOffIcon from "@mui/icons-material/PowerOff";
import ScheduleOutlinedIcon from "@mui/icons-material/ScheduleOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import { toast } from "react-toastify";
import { useTranslation } from "react-i18next";
import dayjs from "dayjs";
import ConfirmButton from "@/components/shared/ConfirmButton";
import MapAutocomplete from "@/components/shared/MapAutocomplete";
import { PlayerDrawerLink } from "@/components/shared/PlayerDrawerLink";
import { useAuth } from "@/hooks/useAuth";
import { isFakeMode } from "@/mirage/demo-data";
import { getMapEnvironmentLabel, getMapModeLabel } from "@/utils/mapLabels";
import { cmd } from "@/utils/fetchUtils";
import {
  getMapLayerImageSrc,
  unifiedGamemodeName,
} from "../../objectives/helpers";
import {
  mapsManagerMutationOptions,
  mapsManagerQueryKeys,
  mapsManagerQueryOptions,
} from "../../queries";

const MAX_HISTORY_ITEMS = 4;

const errorToast = (error) => {
  toast.error(
    <div>
      <span>{error.name}</span>
      <p>{error.message}</p>
    </div>
  );
};

function SummaryCell({ icon, label, value, detail, color = "text.primary" }) {
  return (
    <Stack
      direction="row"
      spacing={1.25}
      sx={{ minWidth: 0, minHeight: 96, p: { xs: 1.25, sm: 2 } }}
    >
      <Box sx={{ display: "grid", color: "primary.main", mt: 0.2 }}>{icon}</Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography
          variant="overline"
          color="text.secondary"
          sx={{ display: "block", lineHeight: 1.2, overflowWrap: "anywhere" }}
        >
          {label}
        </Typography>
        <Typography
          variant="body1"
          fontWeight={850}
          color={color}
          sx={{ overflowWrap: "anywhere" }}
        >
          {value}
        </Typography>
        {detail && (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: "block", mt: 0.25, lineHeight: 1.35 }}
          >
            {detail}
          </Typography>
        )}
      </Box>
    </Stack>
  );
}

function VotersButton({ mapId, voters = [] }) {
  const { t } = useTranslation();
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);
  const popoverId = open ? `${mapId}-voters` : undefined;

  return (
    <>
      <IconButton
        aria-label={t("maps.votemapWorkbench.showVoters")}
        aria-describedby={popoverId}
        onClick={(event) => setAnchorEl(event.currentTarget)}
        sx={{ width: 44, height: 44 }}
      >
        <VisibilityOutlinedIcon fontSize="small" />
      </IconButton>
      <Popover
        id={popoverId}
        open={open}
        anchorEl={anchorEl}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
      >
        <Box sx={{ minWidth: 260, maxHeight: 320, overflowY: "auto" }}>
          <Typography
            variant="overline"
            color="primary.main"
            sx={{ display: "block", px: 2, py: 1.25 }}
          >
            {t("maps.votemapWorkbench.voters", { count: voters.length })}
          </Typography>
          <Divider />
          {voters.length ? (
            voters.map((voter, index) => (
              <Box
                key={voter.player_id ?? index}
                sx={{
                  px: 2,
                  py: 1,
                  borderBottom: "1px solid",
                  borderColor: "divider",
                }}
              >
                <PlayerDrawerLink playerId={voter.player_id}>
                  {voter.player_name}: {voter.count}
                </PlayerDrawerLink>
              </Box>
            ))
          ) : (
            <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
              {t("maps.votemapWorkbench.noVoters")}
            </Typography>
          )}
        </Box>
      </Popover>
    </>
  );
}

function VoteRow({
  result,
  index,
  rank,
  isLeading,
  totalVotes,
  playerChoice,
  onRemove,
  canRemove,
}) {
  const { t } = useTranslation();
  const mapLayer = result.map;
  const votes = Number(result.votes_count) || 0;
  const share = totalVotes ? Math.round((votes / totalVotes) * 100) : 0;
  const mode = unifiedGamemodeName(mapLayer.game_mode);
  const isPlayerChoice = Boolean(playerChoice && index === 0);

  return (
    <Box
      component="article"
      sx={{
        display: "grid",
        gridTemplateColumns: {
          xs: "42px minmax(0, 1fr) 44px 88px",
          sm: "42px minmax(180px, 1.35fr) minmax(120px, 1fr) 56px 88px",
        },
        alignItems: "center",
        minHeight: 68,
        borderBottom: "1px solid",
        borderColor: "divider",
        bgcolor: isLeading ? "action.selected" : "transparent",
      }}
    >
      <Box sx={{ px: 1.25 }}>
        <Box
          sx={{
            display: "grid",
            placeItems: "center",
            width: 30,
            height: 30,
            border: "1px solid",
            borderColor: isLeading ? "success.main" : "divider",
            color: isLeading ? "success.main" : "text.secondary",
            fontWeight: 850,
          }}
        >
          {rank ?? "–"}
        </Box>
      </Box>

      <Stack
        direction="row"
        spacing={1.25}
        alignItems="center"
        sx={{ minWidth: 0 }}
      >
        <Box
          component="img"
          src={getMapLayerImageSrc(mapLayer)}
          alt=""
          sx={{
            width: 88,
            height: 50,
            objectFit: "cover",
            display: { xs: "none", sm: "block" },
          }}
        />
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="body2" fontWeight={850} noWrap>
            {mapLayer.map.pretty_name}
          </Typography>
          <Typography variant="caption" color="text.secondary" noWrap>
            {getMapModeLabel(t, mode)} ·{" "}
            {getMapEnvironmentLabel(t, mapLayer.environment)}
          </Typography>
          {isPlayerChoice && (
            <Typography
              variant="caption"
              color="warning.main"
              sx={{ display: "block" }}
            >
              {t("maps.votemapStatus.playerChoice", {
                player: playerChoice.player_name,
              })}
            </Typography>
          )}
        </Box>
      </Stack>

      <Stack
        spacing={0.5}
        sx={{ px: 1.5, display: { xs: "none", sm: "flex" } }}
      >
        <LinearProgress
          variant="determinate"
          value={share}
          color={isLeading ? "success" : "primary"}
        />
        <Typography variant="caption" color="text.secondary">
          {t("maps.votemapWorkbench.voteShare", { share })}
        </Typography>
      </Stack>

      <Typography
        variant="body2"
        fontWeight={850}
        textAlign="right"
        color={isLeading ? "success.main" : "text.primary"}
        sx={{ pr: { xs: 0, sm: 1 } }}
      >
        {votes}
      </Typography>

      <Stack direction="row" justifyContent="flex-end" sx={{ pr: 0.5 }}>
        <VotersButton mapId={mapLayer.id} voters={result.voters ?? []} />
        {canRemove && (
          <ConfirmButton
            onConfirm={() => onRemove(mapLayer)}
            title={t("maps.votemapWorkbench.removeTitle", {
              map: mapLayer.map.pretty_name,
            })}
            description={t("maps.votemapWorkbench.removeDescription")}
            buttonText={<CloseIcon fontSize="small" />}
            buttonProps={{
              variant: "text",
              color: "error",
              "aria-label": t("maps.votemapWorkbench.removeMap", {
                map: mapLayer.map.pretty_name,
              }),
              sx: { minWidth: 44, width: 44, height: 44, p: 0 },
            }}
          />
        )}
      </Stack>
    </Box>
  );
}

function CurrentVote({ status, onRemove, canRemove }) {
  const { t } = useTranslation();
  const results = status.results ?? [];
  const totalVotes = results.reduce(
    (sum, result) => sum + (Number(result.votes_count) || 0),
    0
  );
  const rankedVoteCounts = [
    ...new Set(results.map((result) => Number(result.votes_count) || 0)),
  ].sort((a, b) => b - a);

  return (
    <Box component="section" aria-labelledby="current-vote-heading">
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="end"
        sx={{ mb: 1 }}
      >
        <Box>
          <Typography variant="overline" color="primary.main">
            {t("maps.votemapWorkbench.liveEyebrow")}
          </Typography>
          <Typography
            id="current-vote-heading"
            component="h2"
            variant="h6"
            fontWeight={850}
          >
            {t("maps.votemapStatus.currentSelection")}
          </Typography>
        </Box>
        <Typography variant="caption" color="text.secondary">
          {t("maps.votemapWorkbench.optionCount", { count: results.length })}
        </Typography>
      </Stack>

      <Box sx={{ border: "1px solid", borderColor: "divider" }}>
        <Box
          sx={{
            display: { xs: "none", sm: "grid" },
            gridTemplateColumns:
              "42px minmax(180px, 1.35fr) minmax(120px, 1fr) 56px 88px",
            px: 1,
            py: 0.9,
            borderBottom: "1px solid",
            borderColor: "divider",
            bgcolor: "background.default",
          }}
        >
          <Typography variant="overline">#</Typography>
          <Typography variant="overline">
            {t("maps.votemapWorkbench.mapAndMode")}
          </Typography>
          <Typography variant="overline">
            {t("maps.votemapWorkbench.distribution")}
          </Typography>
          <Typography variant="overline" textAlign="right">
            {t("settings.general.votes")}
          </Typography>
          <Typography variant="overline" textAlign="right">
            {t("maps.votemapWorkbench.actions")}
          </Typography>
        </Box>

        {results.length ? (
          results.map((result, index) => {
            const votes = Number(result.votes_count) || 0;
            const rank = rankedVoteCounts.indexOf(votes) + 1;

            return (
              <VoteRow
                key={result.map.id}
                result={result}
                index={index}
                rank={totalVotes > 0 ? rank : null}
                isLeading={totalVotes > 0 && rank === 1}
                totalVotes={totalVotes}
                playerChoice={status.player_choice}
                onRemove={onRemove}
                canRemove={canRemove}
              />
            );
          })
        ) : (
          <Stack
            alignItems="center"
            spacing={1}
            sx={{ py: 7, px: 2, textAlign: "center" }}
          >
            <HowToVoteOutlinedIcon
              sx={{ fontSize: 44, color: "text.disabled" }}
            />
            <Typography variant="h6">
              {status.enabled
                ? t("maps.votemapStatus.emptySelection")
                : t("maps.votemapStatus.disabled")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t("maps.votemapWorkbench.emptyVoteHint")}
            </Typography>
          </Stack>
        )}
      </Box>
    </Box>
  );
}

function History({ results, page, onPageChange }) {
  const { t } = useTranslation();
  const current = results[page - 1];

  return (
    <Box component="section" aria-labelledby="vote-history-heading">
      <Stack
        direction={{ xs: "column", sm: "row" }}
        justifyContent="space-between"
        alignItems={{ xs: "stretch", sm: "center" }}
        gap={1}
        sx={{ mb: 1 }}
      >
        <Box>
          <Typography variant="overline" color="primary.main">
            {t("maps.votemapWorkbench.historyEyebrow")}
          </Typography>
          <Typography
            id="vote-history-heading"
            component="h2"
            variant="h6"
            fontWeight={850}
          >
            {t("maps.votemapStatus.history")}
          </Typography>
        </Box>
        {results.length > 1 && (
          <Pagination
            count={results.length}
            page={page}
            onChange={onPageChange}
            sx={{ "& .MuiPaginationItem-root": { minWidth: 44, height: 44 } }}
          />
        )}
      </Stack>

      <Box sx={{ border: "1px solid", borderColor: "divider" }}>
        {current ? (
          <>
            <Stack
              direction={{ xs: "column", sm: "row" }}
              justifyContent="space-between"
              gap={0.5}
              sx={{ px: 2, py: 1.25, bgcolor: "background.default" }}
            >
              <Typography variant="body2" fontWeight={800}>
                {current.map.pretty_name}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {dayjs.unix(current.ts).format("lll")}
              </Typography>
            </Stack>
            {(current.results ?? [])
              .slice(0, MAX_HISTORY_ITEMS)
              .map((result, index) => (
                <Stack
                  key={result.map.id}
                  direction="row"
                  alignItems="center"
                  justifyContent="space-between"
                  sx={{
                    px: 2,
                    py: 1,
                    borderTop: "1px solid",
                    borderColor: "divider",
                  }}
                >
                  <Typography variant="body2">
                    {index + 1}. {result.map.map.pretty_name}
                  </Typography>
                  <Typography variant="body2" fontWeight={800}>
                    {result.votes_count}
                  </Typography>
                </Stack>
              ))}
          </>
        ) : (
          <Typography variant="body2" color="text.secondary" sx={{ p: 2.5 }}>
            {t("maps.votemapStatus.noHistory")}
          </Typography>
        )}
      </Box>
    </Box>
  );
}

export default function VotemapStatusPage() {
  const { t } = useTranslation();
  const loaderData = useLoaderData();
  const queryClient = useQueryClient();
  const { permissions } = useAuth();
  const fakeMode = isFakeMode();
  const granted = useMemo(
    () =>
      new Set(
        (permissions?.permissions ?? []).map((entry) =>
          typeof entry === "string" ? entry : entry.permission
        )
      ),
    [permissions]
  );
  const can = (permission) =>
    fakeMode || permissions?.is_superuser || granted.has(permission);

  const { data: maps = [] } = useQuery({
    ...mapsManagerQueryOptions.maps(),
    initialData: [],
  });
  const { data: votemapStatus = {}, isFetching: statusRefreshing } = useQuery({
    ...mapsManagerQueryOptions.votemapStatus(),
    initialData: loaderData.votemapStatus,
    refetchInterval: fakeMode ? false : 15_000,
    staleTime: 5_000,
    refetchOnMount: false,
  });
  const { data: votemapResults = [] } = useQuery({
    ...mapsManagerQueryOptions.votemapResults(),
    initialData: loaderData.votemapResults,
    refetchInterval: fakeMode ? false : 60_000,
    staleTime: 5_000,
    refetchOnMount: false,
  });
  const [resultHistoryPage, setResultHistoryPage] = useState(1);
  const [selectedMap, setSelectedMap] = useState(null);
  const results = votemapStatus.results ?? [];
  const totalVotes = results.reduce(
    (sum, result) => sum + (Number(result.votes_count) || 0),
    0
  );

  useEffect(() => {
    setResultHistoryPage((current) =>
      Math.min(Math.max(current, 1), Math.max(votemapResults.length, 1))
    );
  }, [votemapResults.length]);

  const refreshStatus = () =>
    queryClient.invalidateQueries({
      queryKey: mapsManagerQueryKeys.votemapStatus,
    });

  const { mutate: toggleVotemap, isPending: isToggling } = useMutation({
    mutationFn: async () => {
      if (fakeMode) {
        return { arguments: { enabled: !votemapStatus.enabled } };
      }
      const config = await cmd.GET_VOTEMAP_CONFIG();
      return cmd.SET_VOTEMAP_CONFIG({
        payload: { ...config, enabled: !config.enabled },
        throwRouteError: false,
      });
    },
    onSuccess: (response) => {
      const enabled = response.arguments.enabled;
      if (fakeMode) {
        queryClient.setQueryData(
          mapsManagerQueryKeys.votemapStatus,
          (current) => ({
            ...current,
            enabled,
            paused: false,
          })
        );
        queryClient.setQueryData(
          mapsManagerQueryKeys.voteMapConfig,
          (current) => (current ? { ...current, enabled } : current)
        );
      } else {
        queryClient.invalidateQueries({
          queryKey: mapsManagerQueryKeys.voteMapConfig,
        });
        refreshStatus();
      }
      toast.success(
        t("maps.votemapUpdated", {
          state: enabled ? t("common.enabled") : t("common.disabled"),
        })
      );
    },
    onError: errorToast,
  });

  const { mutate: resetVotemap, isPending: isResetting } = useMutation({
    mutationFn: fakeMode
      ? async () => ({})
      : mapsManagerMutationOptions.resetVotemapState.mutationFn,
    onSuccess: () => {
      if (fakeMode) {
        queryClient.setQueryData(
          mapsManagerQueryKeys.votemapStatus,
          (current) => ({
            ...current,
            next_map: null,
            player_choice: null,
            paused: false,
            results: (current.results ?? []).map((result) => ({
              ...result,
              voters: [],
              votes_count: 0,
            })),
          })
        );
      } else {
        refreshStatus();
      }
      toast.success(t("maps.votemapReset"));
    },
    onError: errorToast,
  });

  const { mutate: sendReminder, isPending: isSendingReminder } = useMutation({
    mutationFn: fakeMode
      ? async () => ({})
      : mapsManagerMutationOptions.sendVotemapReminder.mutationFn,
    onSuccess: () => {
      if (fakeMode) {
        queryClient.setQueryData(
          mapsManagerQueryKeys.votemapStatus,
          (current) => ({
            ...current,
            last_reminder: new Date().toISOString(),
          })
        );
      } else {
        refreshStatus();
      }
      toast.success(t("maps.votemapStatus.reminderSent"));
    },
    onError: errorToast,
  });

  const { mutate: removeMapFromVotemap } = useMutation({
    mutationFn: fakeMode
      ? async (mapLayer) => ({ arguments: { map_name: mapLayer.id } })
      : mapsManagerMutationOptions.removeMapFromVotemap.mutationFn,
    onSuccess: (response) => {
      const mapName = response.arguments.map_name;
      if (fakeMode) {
        queryClient.setQueryData(
          mapsManagerQueryKeys.votemapStatus,
          (current) => ({
            ...current,
            player_choice:
              current.results?.[0]?.map?.id === mapName
                ? null
                : current.player_choice,
            results: (current.results ?? []).filter(
              (result) => result.map.id !== mapName
            ),
          })
        );
      } else {
        refreshStatus();
      }
      toast.success(t("maps.votemapStatus.mapRemoved", { map: mapName }));
    },
    onError: errorToast,
  });

  const { mutate: addMapToVotemap, isPending: isAddingMap } = useMutation({
    mutationFn: fakeMode
      ? async (mapName) => ({ arguments: { map_name: mapName } })
      : mapsManagerMutationOptions.addMapToVotemap.mutationFn,
    onSuccess: (response) => {
      const mapName = response.arguments.map_name;
      if (fakeMode) {
        const mapLayer = maps.find((map) => map.id === mapName);
        if (mapLayer) {
          queryClient.setQueryData(
            mapsManagerQueryKeys.votemapStatus,
            (current) => ({
              ...current,
              results: (current.results ?? []).some(
                (result) => result.map.id === mapName
              )
                ? current.results
                : [
                    ...(current.results ?? []),
                    { map: mapLayer, voters: [], votes_count: 0 },
                  ],
            })
          );
        }
      } else {
        refreshStatus();
      }
      toast.success(t("maps.votemapStatus.mapAdded", { map: mapName }));
    },
    onError: errorToast,
  });

  const { mutate: setVotemapWinner, isPending: isSettingWinner } = useMutation({
    mutationFn: fakeMode
      ? async (mapName) => ({ arguments: { map_name: mapName } })
      : mapsManagerMutationOptions.setVotemapWinner.mutationFn,
    onSuccess: (response) => {
      const mapName = response.arguments.map_name;
      if (fakeMode) {
        const mapLayer = maps.find((map) => map.id === mapName);
        queryClient.setQueryData(
          mapsManagerQueryKeys.votemapStatus,
          (current) => ({
            ...current,
            next_map: mapLayer?.map?.pretty_name ?? mapName,
            paused: true,
          })
        );
      } else {
        refreshStatus();
      }
      toast.success(t("maps.votemapStatus.winnerSet", { map: mapName }));
    },
    onError: errorToast,
  });

  const active = Boolean(votemapStatus.enabled);
  const statusLabel = votemapStatus.paused
    ? t("maps.votemapWorkbench.paused")
    : active
    ? t("common.enabled")
    : t("common.disabled");

  return (
    <Box sx={{ p: { xs: 1.5, md: 2.5 } }}>
      <Box
        role="status"
        aria-live="polite"
        sx={{
          position: "absolute",
          width: "1px",
          height: "1px",
          p: 0,
          m: -1,
          overflow: "hidden",
          clip: "rect(0 0 0 0)",
          whiteSpace: "nowrap",
          border: 0,
        }}
      >
        {statusLabel}
      </Box>
      <Box
        component="aside"
        aria-label={t("maps.votemapWorkbench.summary")}
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "repeat(2, minmax(0, 1fr))",
            sm: "repeat(2, minmax(0, 1fr))",
            lg: "repeat(4, minmax(0, 1fr))",
          },
          gap: "1px",
          bgcolor: "divider",
          border: "1px solid",
          borderColor: "divider",
          mb: 2.5,
          "& > *": {
            bgcolor: "background.paper",
          },
        }}
      >
        <SummaryCell
          icon={
            active ? (
              <CheckCircleOutlineIcon fontSize="small" />
            ) : (
              <PowerOffIcon fontSize="small" />
            )
          }
          label={t("maps.status")}
          value={statusLabel}
          detail={
            statusRefreshing
              ? t("maps.votemapWorkbench.updating")
              : t("maps.votemapWorkbench.liveStatus")
          }
          color={active ? "success.main" : "text.secondary"}
        />
        <SummaryCell
          icon={<EmojiEventsOutlinedIcon fontSize="small" />}
          label={t("maps.next")}
          value={
            active
              ? votemapStatus.next_map ?? t("maps.votemapWorkbench.open")
              : "–"
          }
          detail={t("maps.votemapWorkbench.decidedAfterVote")}
        />
        <SummaryCell
          icon={<HowToVoteOutlinedIcon fontSize="small" />}
          label={t("maps.votemapWorkbench.totalVotes")}
          value={String(totalVotes)}
          detail={t("maps.votemapWorkbench.optionCount", {
            count: results.length,
          })}
        />
        <SummaryCell
          icon={<ScheduleOutlinedIcon fontSize="small" />}
          label={t("maps.votemapStatus.lastReminder")}
          value={
            votemapStatus.last_reminder
              ? dayjs(votemapStatus.last_reminder).fromNow()
              : "–"
          }
          detail={t("maps.votemapWorkbench.automaticRefresh")}
        />
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1fr) 320px" },
          gridTemplateAreas: {
            xs: '"current" "actions" "history"',
            lg: '"current actions" "history actions"',
          },
          gap: 2.5,
          alignItems: "start",
        }}
      >
        <Box sx={{ gridArea: "current", minWidth: 0 }}>
          <CurrentVote
            status={votemapStatus}
            onRemove={removeMapFromVotemap}
            canRemove={can("can_remove_map_from_votemap") && active}
          />
        </Box>
        <Box
          component="aside"
          aria-labelledby="vote-actions-heading"
          sx={{
            gridArea: "actions",
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          <Box
            sx={{
              px: 2,
              py: 1.5,
              bgcolor: "background.default",
              borderBottom: "1px solid",
              borderColor: "divider",
            }}
          >
            <Typography variant="overline" color="primary.main">
              {t("maps.votemapWorkbench.controlEyebrow")}
            </Typography>
            <Typography
              id="vote-actions-heading"
              component="h2"
              variant="h6"
              fontWeight={850}
            >
              {t("maps.votemapWorkbench.controlTitle")}
            </Typography>
          </Box>

          <Stack spacing={1.25} sx={{ p: 2 }}>
            <MapAutocomplete
              options={maps}
              selected={selectedMap}
              onSelect={setSelectedMap}
              label={t("maps.votemapStatus.selectMap")}
            />
            <Typography variant="caption" color="text.secondary">
              {t("maps.votemapWorkbench.selectionHint")}
            </Typography>

            <Button
              variant="outlined"
              startIcon={
                isAddingMap ? <CircularProgress size={18} /> : <AddIcon />
              }
              disabled={
                !active ||
                !selectedMap ||
                isAddingMap ||
                !can("can_add_map_to_votemap")
              }
              onClick={() => addMapToVotemap(selectedMap)}
              sx={{ minHeight: 44, justifyContent: "flex-start" }}
            >
              {t("maps.votemapStatus.add")}
            </Button>

            <ConfirmButton
              disabled={
                !active ||
                !selectedMap ||
                isSettingWinner ||
                !can("can_set_votemap_winner")
              }
              onConfirm={() => setVotemapWinner(selectedMap)}
              title={t("maps.votemapWorkbench.winnerTitle")}
              description={t("maps.votemapWorkbench.winnerDescription")}
              buttonText={t("maps.votemapStatus.setWinner")}
              buttonProps={{
                variant: "outlined",
                color: "warning",
                fullWidth: true,
                startIcon: isSettingWinner ? (
                  <CircularProgress size={18} />
                ) : (
                  <EmojiEventsOutlinedIcon />
                ),
                sx: { minHeight: 44, justifyContent: "flex-start" },
              }}
            />

            <Divider />

            <Button
              variant="outlined"
              startIcon={
                isSendingReminder ? (
                  <CircularProgress size={18} />
                ) : (
                  <AnnouncementOutlinedIcon />
                )
              }
              disabled={
                !active ||
                isSendingReminder ||
                !can("can_send_votemap_reminder")
              }
              onClick={sendReminder}
              sx={{ minHeight: 44, justifyContent: "flex-start" }}
            >
              {t("maps.votemapStatus.remind")}
            </Button>

            <ConfirmButton
              disabled={
                !active || isResetting || !can("can_reset_votemap_state")
              }
              onConfirm={resetVotemap}
              title={t("maps.votemapWorkbench.resetTitle")}
              description={t("maps.votemapWorkbench.resetDescription")}
              buttonText={t("maps.resetVotemap")}
              buttonProps={{
                variant: "outlined",
                color: "warning",
                fullWidth: true,
                startIcon: isResetting ? (
                  <CircularProgress size={18} />
                ) : (
                  <AutorenewIcon />
                ),
                sx: { minHeight: 44, justifyContent: "flex-start" },
              }}
            />

            <ConfirmButton
              disabled={isToggling || !can("can_change_votemap_config")}
              onConfirm={toggleVotemap}
              title={t(
                active
                  ? "maps.votemapWorkbench.disableTitle"
                  : "maps.votemapWorkbench.enableTitle"
              )}
              description={t(
                active
                  ? "maps.disableVotemapDescription"
                  : "maps.enableVotemapDescription"
              )}
              buttonText={
                active ? t("maps.disableVotemap") : t("maps.enableVotemap")
              }
              buttonProps={{
                variant: "contained",
                color: active ? "error" : "success",
                fullWidth: true,
                startIcon: isToggling ? (
                  <CircularProgress size={18} />
                ) : active ? (
                  <PowerOffIcon />
                ) : (
                  <PowerIcon />
                ),
                sx: { minHeight: 44, justifyContent: "flex-start" },
              }}
            />
          </Stack>
        </Box>
        <Box sx={{ gridArea: "history", minWidth: 0 }}>
          <History
            results={votemapResults}
            page={resultHistoryPage}
            onPageChange={(_, value) => setResultHistoryPage(value)}
          />
        </Box>
      </Box>
    </Box>
  );
}
