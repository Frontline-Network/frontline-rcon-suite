import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  mapsManagerMutationOptions,
  mapsManagerQueryKeys,
  mapsManagerQueryOptions,
} from "../../queries";
import { MapList } from "../../MapList";
import {
  MapVotemapListItem,
  MapVotemapResultListItem,
} from "../../MapListItem";
import {
  Box,
  Button,
  CircularProgress,
  Divider,
  Pagination,
  Stack,
  styled,
  Typography,
} from "@mui/material";
import PowerOffIcon from "@mui/icons-material/PowerOff";
import PowerIcon from "@mui/icons-material/Power";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import AnnouncementIcon from "@mui/icons-material/Announcement";
import AddIcon from "@mui/icons-material/Add";
import PauseCircleOutlineIcon from "@mui/icons-material/PauseCircleOutline";
import { useLoaderData } from "react-router-dom";
import { toast } from "react-toastify";
import { useTranslation } from "react-i18next";
import dayjs from "dayjs";
import { useState } from "react";
import MapAutocomplete from "@/components/shared/MapAutocomplete";
import { cmd } from "@/utils/fetchUtils";

const MapListContainer = styled(Box)(({ theme }) => ({
  width: "100%",
  [theme.breakpoints.up("md")]: {
    width: "50%",
  },
}));

const ActionsContainer = styled(Box)(({ theme }) => ({
  width: "100%",
  padding: theme.spacing(1),
  [theme.breakpoints.up("md")]: {
    width: "50%",
    borderLeft: `1px solid ${theme.palette.divider}`,
  },
}));

function VotemapStatusPage() {
  const { t } = useTranslation();
  const loaderData = useLoaderData();
  const queryClient = useQueryClient();

  const { data: maps } = useQuery({
    ...mapsManagerQueryOptions.maps(),
    initialData: [],
  });

  const { data: votemapStatus } = useQuery({
    ...mapsManagerQueryOptions.votemapStatus(),
    initialData: loaderData.votemapStatus,
    refetchInterval: 15_000,
    staleTime: 5_000,
    refetchOnMount: false,
  });

  const { data: votemapResults } = useQuery({
    ...mapsManagerQueryOptions.votemapResults(),
    initialData: loaderData.votemapResults,
    refetchInterval: 60_000,
    staleTime: 5_000,
    refetchOnMount: false,
  });
  const [resultHistoryPage, setResultHistoryPage] = useState(1);
  const handleResultHistoryPageChange = (event, value) => {
    setResultHistoryPage(value);
  };
  const [selectedMap, setSelectedMap] = useState(null);

  const { mutate: toggleVotemap, isPending: isToggling } = useMutation({
    mutationFn: async () => {
      const config = await cmd.GET_VOTEMAP_CONFIG();
      return cmd.SET_VOTEMAP_CONFIG({
        payload: {
          ...config,
          enabled: !config.enabled,
        },
        throwRouteError: false,
      });
    },
    onSuccess: (response) => {
      const enabled = response.arguments.enabled;
      queryClient.invalidateQueries({
        queryKey: mapsManagerQueryKeys.voteMapConfig,
      });
      queryClient.invalidateQueries({
        queryKey: mapsManagerQueryKeys.votemapStatus,
      });
      toast.success(
        t("maps.votemapUpdated", {
          state: enabled ? t("common.enabled") : t("common.disabled"),
        })
      );
    },
    onError: (error) => {
      toast.error(
        <div>
          <span>{error.name}</span>
          <p>{error.message}</p>
        </div>
      );
    },
  });

  const { mutate: resetVotemap, isPending: isReseting } = useMutation({
    ...mapsManagerMutationOptions.resetVotemapState,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: mapsManagerQueryKeys.votemapStatus,
      });
      toast.success(t("maps.votemapReset"));
    },
    onError: (error) => {
      toast.error(
        <div>
          <span>{error.name}</span>
          <p>{error.message}</p>
        </div>
      );
    },
  });

  const { mutate: sendReminder, isPending: isSendingReminder } = useMutation({
    ...mapsManagerMutationOptions.sendVotemapReminder,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: mapsManagerQueryKeys.votemapStatus,
      });
      toast.success(t("maps.votemapStatus.reminderSent"));
    },
    onError: (error) => {
      toast.error(
        <div>
          <span>{error.name}</span>
          <p>{error.message}</p>
        </div>
      );
    },
  });

  const { mutate: removeMapFromVotemap } = useMutation({
    ...mapsManagerMutationOptions.removeMapFromVotemap,
    onSuccess: (response) => {
      const mapName = response.arguments.map_name;
      queryClient.invalidateQueries({
        queryKey: mapsManagerQueryKeys.votemapStatus,
      });
      toast.success(t("maps.votemapStatus.mapRemoved", { map: mapName }));
    },
    onError: (error) => {
      toast.error(
        <div>
          <span>{error.name}</span>
          <p>{error.message}</p>
        </div>
      );
    },
  });

  const { mutate: addMapToVotemap, isPending: isAddingMapToVotemap } =
    useMutation({
      ...mapsManagerMutationOptions.addMapToVotemap,
      onSuccess: (response) => {
        const mapName = response.arguments.map_name;
        queryClient.invalidateQueries({
          queryKey: mapsManagerQueryKeys.votemapStatus,
        });
        toast.success(t("maps.votemapStatus.mapAdded", { map: mapName }));
      },
      onError: (error) => {
        toast.error(
          <div>
            <span>{error.name}</span>
            <p>{error.message}</p>
          </div>
        );
      },
    });

  const { mutate: setVotemapWinner, isPending: isSettingVotemapWinner } =
    useMutation({
      ...mapsManagerMutationOptions.setVotemapWinner,
      onSuccess: (response) => {
        const mapName = response.arguments.map_name;
        queryClient.invalidateQueries({
          queryKey: mapsManagerQueryKeys.votemapStatus,
        });
        toast.success(t("maps.votemapStatus.winnerSet", { map: mapName }));
      },
      onError: (error) => {
        toast.error(
          <div>
            <span>{error.name}</span>
            <p>{error.message}</p>
          </div>
        );
      },
    });

  const handleVotemapToggle = () => {
    toggleVotemap();
  };

  return (
    <Stack direction={{ xs: "column-reverse", md: "row" }} spacing={1}>
      <MapListContainer>
        <Typography variant="h6">
          {t("maps.votemapStatus.currentSelection")}
        </Typography>
        <MapList
          maps={(votemapStatus?.results ?? []).map((s) => s.map)}
          emptyListMessage={
            votemapStatus?.enabled
              ? t("maps.votemapStatus.emptySelection")
              : t("maps.votemapStatus.disabled")
          }
          sort={false}
          renderItem={(mapLayer, index) => {
            return votemapStatus?.player_choice && index === 0 ? (
              <Box sx={{ py: 2 }}>
                <Typography variant="subtitle2">
                  {t("maps.votemapStatus.playerChoice", {
                    player: votemapStatus.player_choice.player_name,
                  })}
                </Typography>
                <MapVotemapListItem
                  key={mapLayer.id}
                  mapLayer={mapLayer}
                  voters={votemapStatus.results[index].voters}
                  votesCount={votemapStatus.results[index].votes_count}
                  onClick={removeMapFromVotemap}
                  isPlayerChoice={votemapStatus.player_choice}
                />
              </Box>
            ) : (
              <MapVotemapListItem
                key={mapLayer.id}
                mapLayer={mapLayer}
                voters={votemapStatus.results[index].voters}
                votesCount={votemapStatus.results[index].votes_count}
                onClick={removeMapFromVotemap}
                isPlayerChoice={votemapStatus.player_choice}
              />
            );
          }}
        />
        <Divider flexItem orientation="horizontal" sx={{ my: 1 }} />
        <Stack spacing={1}>
          <Typography variant="h6">
            {t("maps.votemapStatus.history")}
          </Typography>
          {votemapResults.length > 0 ? (
            <>
              <Pagination
                size="small"
                count={votemapResults.length}
                page={resultHistoryPage}
                onChange={handleResultHistoryPageChange}
              />
              <Typography>
                {t("maps.votemapStatus.resultRecorded", {
                  date: dayjs
                    .unix(votemapResults[resultHistoryPage - 1].ts)
                    .format("lll"),
                  map: votemapResults[resultHistoryPage - 1].map.pretty_name,
                })}
              </Typography>
              <MapList
                maps={votemapResults[resultHistoryPage - 1].results.map(
                  (s) => s.map
                )}
                emptyListMessage={t("maps.votemapStatus.emptyHistoryResult")}
                sort={false}
                renderItem={(mapLayer, index) => (
                  <MapVotemapResultListItem
                    key={mapLayer.id}
                    mapLayer={mapLayer}
                    votesCount={
                      votemapResults[resultHistoryPage - 1].results[index]
                        .votes_count
                    }
                  />
                )}
              />
            </>
          ) : (
            <Typography>{t("maps.votemapStatus.noHistory")}</Typography>
          )}
        </Stack>
      </MapListContainer>
      <ActionsContainer>
        <Typography variant="subtitle2" component={"div"}>
          {t("maps.status")}:{" "}
          {votemapStatus.enabled
            ? "🟢 " + t("common.enabled")
            : "🔴 " + t("common.disabled")}{" "}
          {votemapStatus.paused && t("maps.votemapStatus.paused")}
        </Typography>
        <Typography variant="subtitle2" component={"div"}>
          {t("maps.next")}:{" "}
          {votemapStatus.enabled
            ? votemapStatus.next_map ?? t("common.unknown")
            : "–"}
        </Typography>
        <Typography variant="subtitle2" component={"div"}>
          {t("maps.votemapStatus.lastReminder")}:{" "}
          {votemapStatus.last_reminder
            ? dayjs(votemapStatus.last_reminder).fromNow()
            : "–"}
        </Typography>
        <Divider orientation="horizontal" sx={{ my: 1 }} />
        <Stack direction="row" spacing={1} alignItems={"center"}>
          <Button
            onClick={handleVotemapToggle}
            startIcon={
              isToggling ? (
                <CircularProgress size={20} />
              ) : votemapStatus.enabled ? (
                <PowerOffIcon />
              ) : (
                <PowerIcon />
              )
            }
            variant="contained"
            disabled={isToggling}
            color={votemapStatus.enabled ? "error" : "success"}
            sx={{ minWidth: 120 }}
            size="small"
          >
            {votemapStatus.enabled
              ? t("maps.disableVotemap")
              : t("maps.enableVotemap")}
          </Button>
          <Typography variant="caption">
            {votemapStatus.enabled
              ? t("maps.disableVotemapDescription")
              : t("maps.enableVotemapDescription")}
          </Typography>
        </Stack>
        <Divider flexItem orientation="horizontal" sx={{ my: 1 }} />
        <Stack direction="row" spacing={1} alignItems={"center"}>
          <Button
            onClick={resetVotemap}
            disabled={isReseting || !votemapStatus.enabled}
            startIcon={
              isReseting ? <CircularProgress size={20} /> : <AutorenewIcon />
            }
            variant="contained"
            color="warning"
            sx={{ minWidth: 120 }}
            size="small"
          >
            {t("maps.resetVotemap")}
          </Button>
          <Typography variant="caption">
            {t("maps.resetVotemapDescription")}
          </Typography>
        </Stack>
        <Divider flexItem orientation="horizontal" sx={{ my: 1 }} />
        <Stack direction="row" spacing={1} alignItems={"center"}>
          <Button
            onClick={sendReminder}
            disabled={isSendingReminder || !votemapStatus.enabled}
            startIcon={
              isSendingReminder ? (
                <CircularProgress size={20} />
              ) : (
                <AnnouncementIcon />
              )
            }
            variant="contained"
            sx={{ minWidth: 120 }}
            size="small"
          >
            {t("maps.votemapStatus.remind")}
          </Button>
          <Typography variant="caption">
            {t("maps.votemapStatus.remindHelp")}
          </Typography>
        </Stack>
        <Divider flexItem orientation="horizontal" sx={{ my: 2 }} />
        <Stack spacing={2}>
          <Stack direction="row" spacing={1} alignItems={"center"}>
            <Button
              onClick={() => {
                addMapToVotemap(selectedMap);
              }}
              disabled={
                !selectedMap || isAddingMapToVotemap || !votemapStatus.enabled
              }
              startIcon={
                isAddingMapToVotemap ? (
                  <CircularProgress size={20} />
                ) : (
                  <AddIcon />
                )
              }
              variant="contained"
              sx={{ minWidth: 120 }}
              size="small"
            >
              {t("maps.votemapStatus.add")}
            </Button>
            <Typography variant="caption">
              {t("maps.votemapStatus.addHelp")}
            </Typography>
          </Stack>
          <Stack direction="row" spacing={1} alignItems={"center"}>
            <Button
              onClick={() => {
                setVotemapWinner(selectedMap);
              }}
              disabled={
                !selectedMap || isSettingVotemapWinner || !votemapStatus.enabled
              }
              startIcon={
                isSettingVotemapWinner ? (
                  <CircularProgress size={20} />
                ) : (
                  <PauseCircleOutlineIcon />
                )
              }
              variant="contained"
              color="warning"
              sx={{ minWidth: 120 }}
              size="small"
            >
              {t("maps.votemapStatus.setWinner")}
            </Button>
            <Typography variant="caption">
              {t("maps.votemapStatus.setWinnerHelp")}
            </Typography>
          </Stack>
          <MapAutocomplete
            options={maps}
            selected={selectedMap}
            onSelect={(newMapId) => setSelectedMap(newMapId)}
            label={t("maps.votemapStatus.selectMap")}
          />
        </Stack>
        <Divider flexItem orientation="horizontal" sx={{ my: 2 }} />
      </ActionsContainer>
    </Stack>
  );
}

export default VotemapStatusPage;
