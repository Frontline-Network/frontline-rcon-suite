import { useCallback, useState } from "react";
import { useRouteLoaderData } from "react-router-dom";
import {
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  Typography,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import HistoryToggleOffOutlinedIcon from "@mui/icons-material/HistoryToggleOffOutlined";
import MapOutlinedIcon from "@mui/icons-material/MapOutlined";
import PeopleAltOutlinedIcon from "@mui/icons-material/PeopleAltOutlined";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "react-toastify";
import { useTranslation } from "react-i18next";
import { useGlobalStore } from "@/stores/global-state";
import { getMapEnvironmentLabel, getMapModeLabel } from "@/utils/mapLabels";
import {
  getMapLayerImageSrc,
  unifiedGamemodeName,
} from "../objectives/helpers";
import { MapFilter } from "../MapFilter";
import { MapList } from "../MapList";
import { MapChangeListItem } from "../MapListItem";
import { mapsManagerMutationOptions, mapsManagerQueryKeys } from "../queries";

function MapStateCard({ eyebrow, mapLayer, actionLabel, actionIcon, onAction }) {
  const { t } = useTranslation();
  if (!mapLayer) return null;
  const mode = unifiedGamemodeName(mapLayer.game_mode);

  return (
    <Box
      component="article"
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "104px minmax(0, 1fr)", sm: "150px minmax(0, 1fr) auto" },
        minHeight: { xs: 104, sm: 118 },
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.paper",
      }}
    >
      <Box
        component="img"
        src={getMapLayerImageSrc(mapLayer)}
        alt=""
        sx={{
          width: "100%",
          height: "100%",
          minHeight: { xs: 104, sm: 118 },
          objectFit: "cover",
        }}
      />
      <Stack justifyContent="center" sx={{ px: { xs: 1.5, sm: 2 }, minWidth: 0 }}>
        <Typography variant="overline" color="primary.main">
          {eyebrow}
        </Typography>
        <Typography variant="h6" fontWeight={850} noWrap>
          {mapLayer.map.pretty_name}
        </Typography>
        <Typography variant="caption" color="text.secondary" noWrap>
          {getMapModeLabel(t, mode)}
          {mode === "offensive" && mapLayer.attackers
            ? ` (${mapLayer.attackers})`
            : ""}{" "}
          · {getMapEnvironmentLabel(t, mapLayer.environment)}
        </Typography>
      </Stack>
      <Button
        variant="text"
        color="primary"
        onClick={() => onAction(mapLayer)}
        startIcon={actionIcon}
        sx={{
          minWidth: { sm: 162 },
          borderLeft: { sm: "1px solid" },
          borderTop: { xs: "1px solid", sm: 0 },
          borderColor: "divider",
          gridColumn: { xs: "1 / -1", sm: "auto" },
          minHeight: 48,
        }}
      >
        {actionLabel}
      </Button>
    </Box>
  );
}

function ImpactMetric({ icon, label, value }) {
  return (
    <Stack direction="row" spacing={1} alignItems="center">
      <Box sx={{ color: "primary.main", display: "grid", placeItems: "center" }}>
        {icon}
      </Box>
      <Box>
        <Typography variant="overline" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="body2" fontWeight={850}>
          {value}
        </Typography>
      </Box>
    </Stack>
  );
}

const MapListPage = () => {
  const { t } = useTranslation();
  const { maps } = useRouteLoaderData("maps");
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [mapToConfirm, setMapToConfirm] = useState(null);
  const [filteredMaps, setFilteredMaps] = useState(maps);
  const serverState = useGlobalStore((state) => state.serverState);
  const gameState = useGlobalStore((state) => state.gameState);
  const status = useGlobalStore((state) => state.status);
  const queryClient = useQueryClient();

  const { mutate: changeMap, isPending } = useMutation({
    ...mapsManagerMutationOptions.changeMap,
    onSuccess: (response) => {
      const mapName = response.arguments.map_name;
      queryClient.invalidateQueries({
        queryKey: mapsManagerQueryKeys.gameState,
      });
      toast.success(t("maps.changed", { map: mapName }), {
        toastId: "map-change-success",
      });
      setConfirmDialogOpen(false);
      setMapToConfirm(null);
    },
    onError: (error) => {
      toast.error(
        <div>
          <span>{error.name}</span>
          <p>{error.message}</p>
        </div>,
        { toastId: "map-change-error" }
      );
      setConfirmDialogOpen(false);
    },
  });

  const openConfirmation = (mapLayer) => {
    setMapToConfirm(mapLayer);
    setConfirmDialogOpen(true);
  };
  const closeConfirmation = () => {
    if (isPending) return;
    setConfirmDialogOpen(false);
    setMapToConfirm(null);
  };
  const confirmMapChange = () => {
    if (mapToConfirm) changeMap(mapToConfirm.mapId || mapToConfirm.id);
  };
  const handleFilterChange = useCallback(
    (nextMaps) => setFilteredMaps(nextMaps),
    []
  );

  const currentPlayers = status?.current_players;
  const maxPlayers = status?.max_players;
  const playerImpact =
    currentPlayers != null
      ? maxPlayers != null
        ? `${currentPlayers} / ${maxPlayers}`
        : String(currentPlayers)
      : t("common.unknown");

  return (
    <Box
      data-testid="map-change-workbench"
      sx={{
        width: "auto",
        minWidth: 0,
        maxWidth: 1540,
        mx: "auto",
        pb: 3,
        "& .MuiButton-root, & .MuiIconButton-root, & .MuiOutlinedInput-root, & .MuiOutlinedInput-notchedOutline, & .MuiPaper-root":
          { borderRadius: 0 },
      }}
    >
      <Box component="header" sx={{ mb: 1.5 }}>
        <Typography
          variant="overline"
          color="primary.main"
          sx={{ display: "block", letterSpacing: "0.08em", mb: 0.25 }}
        >
          {t("maps.changeWorkbench.eyebrow")}
        </Typography>
        <Typography component="h1" variant="h4" fontWeight={850}>
          {t("maps.changeWorkbench.title")}
        </Typography>
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ mt: 0.5, maxWidth: 880 }}
        >
          {t("maps.changeWorkbench.subtitle")}
        </Typography>
      </Box>

      {gameState && (
        <Box
          component="section"
          aria-label={t("maps.changeWorkbench.liveState")}
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" },
            gap: 1.5,
            mb: 1.5,
          }}
        >
          <MapStateCard
            eyebrow={t("maps.current")}
            mapLayer={gameState.current_map}
            actionLabel={t("maps.restart")}
            actionIcon={<RestartAltIcon />}
            onAction={openConfirmation}
          />
          <MapStateCard
            eyebrow={t("maps.next")}
            mapLayer={gameState.next_map}
            actionLabel={t("maps.changeWorkbench.switchNow")}
            actionIcon={<PlayArrowIcon />}
            onAction={openConfirmation}
          />
        </Box>
      )}

      <Box
        component="section"
        sx={{
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.paper",
        }}
      >
        <Stack
          direction={{ xs: "column", sm: "row" }}
          justifyContent="space-between"
          gap={1}
          sx={{
            px: 2,
            py: 1.5,
            borderBottom: "1px solid",
            borderColor: "divider",
            bgcolor: "background.default",
          }}
        >
          <Box>
            <Typography component="h2" variant="h6" fontWeight={850}>
              {t("maps.changeWorkbench.catalogTitle")}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {t("maps.changeWorkbench.catalogDescription")}
            </Typography>
          </Box>
          <Typography variant="overline" color="primary.main">
            {t("maps.rotationWorkbench.results", {
              count: filteredMaps.length,
            })}
          </Typography>
        </Stack>
        <MapFilter maps={maps} onFilterChange={handleFilterChange} compact />
        <Box sx={{ p: 1 }}>
          <MapList
            maps={filteredMaps}
            renderItem={(mapLayer) => (
              <MapChangeListItem
                mapLayer={mapLayer}
                key={mapLayer.id}
                onClick={openConfirmation}
                title={t("maps.changeWorkbench.selectMap", {
                  map: mapLayer.map.pretty_name,
                })}
              />
            )}
          />
        </Box>
      </Box>

      <Dialog
        open={confirmDialogOpen}
        onClose={closeConfirmation}
        fullWidth
        maxWidth="sm"
        aria-labelledby="map-change-dialog-title"
        aria-describedby="map-change-dialog-description"
        PaperProps={{ sx: { borderRadius: 0 } }}
      >
        <DialogTitle
          id="map-change-dialog-title"
          sx={{ borderBottom: "1px solid", borderColor: "divider" }}
        >
          <Stack direction="row" spacing={1} alignItems="center">
            <WarningAmberOutlinedIcon color="warning" />
            <Box>
              <Typography variant="overline" color="warning.main">
                {t("maps.changeWorkbench.immediateAction")}
              </Typography>
              <Typography component="span" variant="h6" display="block">
                {t("maps.setCurrent", {
                  map:
                    mapToConfirm?.pretty_name ??
                    mapToConfirm?.map?.pretty_name ??
                    "",
                })}
              </Typography>
            </Box>
          </Stack>
        </DialogTitle>
        <DialogContent sx={{ pt: "20px !important" }}>
          <Typography
            id="map-change-dialog-description"
            variant="body2"
            color="text.secondary"
          >
            {t("maps.timerNotice")}
          </Typography>

          {mapToConfirm && (
            <Box
              sx={{
                mt: 2,
                display: "grid",
                gridTemplateColumns: "112px minmax(0, 1fr)",
                border: "1px solid",
                borderColor: "divider",
              }}
            >
              <Box
                component="img"
                src={getMapLayerImageSrc(mapToConfirm)}
                alt=""
                sx={{ width: "100%", height: "100%", minHeight: 96, objectFit: "cover" }}
              />
              <Stack justifyContent="center" sx={{ px: 2 }}>
                <Typography variant="h6" fontWeight={850}>
                  {mapToConfirm.map.pretty_name}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {getMapModeLabel(
                    t,
                    unifiedGamemodeName(mapToConfirm.game_mode)
                  )}{" "}
                  · {getMapEnvironmentLabel(t, mapToConfirm.environment)}
                </Typography>
              </Stack>
            </Box>
          )}

          <Box
            sx={{
              mt: 2,
              display: "grid",
              gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" },
              gap: 1.5,
              p: 1.5,
              border: "1px solid",
              borderColor: "divider",
              bgcolor: "background.default",
            }}
          >
            <ImpactMetric
              icon={<PeopleAltOutlinedIcon fontSize="small" />}
              label={t("maps.changeWorkbench.playersAffected")}
              value={playerImpact}
            />
            <ImpactMetric
              icon={<HistoryToggleOffOutlinedIcon fontSize="small" />}
              label={t("maps.changeWorkbench.countdown")}
              value={t("maps.changeWorkbench.seconds", { count: 60 })}
            />
            <ImpactMetric
              icon={<MapOutlinedIcon fontSize="small" />}
              label={t("maps.changeWorkbench.targetServer")}
              value={serverState?.name || t("common.unknown")}
            />
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 2, borderTop: "1px solid", borderColor: "divider" }}>
          <Button onClick={closeConfirmation} color="inherit" disabled={isPending}>
            {t("common.cancel")}
          </Button>
          <Button
            onClick={confirmMapChange}
            color="warning"
            variant="contained"
            startIcon={
              isPending ? <CircularProgress size={18} /> : <CheckCircleIcon />
            }
            disabled={isPending}
          >
            {isPending
              ? t("common.loading")
              : t("maps.changeWorkbench.confirmSwitch")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default MapListPage;
