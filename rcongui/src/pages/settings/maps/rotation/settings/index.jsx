import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Box,
  CircularProgress,
  FormControlLabel,
  Stack,
  Switch,
  Typography,
} from "@mui/material";
import AutorenewOutlinedIcon from "@mui/icons-material/AutorenewOutlined";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ReplayIcon from "@mui/icons-material/Replay";
import SaveIcon from "@mui/icons-material/Save";
import ShuffleOutlinedIcon from "@mui/icons-material/ShuffleOutlined";
import { toast } from "react-toastify";
import { useLoaderData } from "react-router-dom";
import { useTranslation } from "react-i18next";
import ConfigActionBar from "@/pages/settings/config-form/ConfigActionBar";
import { getMapEnvironmentLabel, getMapModeLabel } from "@/utils/mapLabels";
import {
  getMapLayerImageSrc,
  unifiedGamemodeName,
} from "../../objectives/helpers";
import {
  mapsManagerMutationOptions,
  mapsManagerQueryKeys,
  mapsManagerQueryOptions,
} from "../../queries";

function SummaryMetric({ label, value, detail, icon }) {
  return (
    <Stack
      className="wardogs-map-summary-metric"
      direction="row"
      spacing={1}
      alignItems="center"
      sx={{
        minHeight: 76,
        p: 1.5,
        borderRight: { xs: 0, sm: "1px solid" },
        borderBottom: { xs: "1px solid", sm: 0 },
        borderColor: "divider",
        "&:last-of-type": { borderRight: 0, borderBottom: 0 },
      }}
    >
      <Box sx={{ color: "primary.main", display: "grid", placeItems: "center" }}>
        {icon}
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography variant="overline" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="body1" fontWeight={850}>
          {value}
        </Typography>
        {detail && (
          <Typography variant="caption" color="text.secondary">
            {detail}
          </Typography>
        )}
      </Box>
    </Stack>
  );
}

function PreviewRow({ mapLayer, index }) {
  const { t } = useTranslation();
  const mode = unifiedGamemodeName(mapLayer.game_mode);
  return (
    <Box
      component="li"
      sx={{
        display: "grid",
        gridTemplateColumns: "42px 82px minmax(0, 1fr)",
        minHeight: 68,
        borderBottom: "1px solid",
        borderColor: "divider",
        "&:last-child": { borderBottom: 0 },
      }}
    >
      <Box sx={{ display: "grid", placeItems: "center" }}>
        <Typography variant="overline" color="primary.main">
          {String(index + 1).padStart(2, "0")}
        </Typography>
      </Box>
      <Box
        component="img"
        src={getMapLayerImageSrc(mapLayer)}
        alt=""
        sx={{ width: "100%", height: "100%", minHeight: 68, objectFit: "cover" }}
      />
      <Stack justifyContent="center" sx={{ px: 1.5, minWidth: 0 }}>
        <Typography variant="body2" fontWeight={850} noWrap>
          {mapLayer.map.pretty_name}
        </Typography>
        <Typography variant="caption" color="text.secondary" noWrap>
          {getMapModeLabel(t, mode)} ·{" "}
          {getMapEnvironmentLabel(t, mapLayer.environment)}
        </Typography>
      </Stack>
    </Box>
  );
}

function MapRotationSettings() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const loaderData = useLoaderData();
  const [draftShuffle, setDraftShuffle] = useState(loaderData.shuffleEnabled);

  const { data: shuffleEnabled } = useQuery({
    ...mapsManagerQueryOptions.mapRotationShuffle(),
    initialData: loaderData.shuffleEnabled,
    refetchOnMount: false,
  });
  const { data: rotation = loaderData.rotation } = useQuery({
    ...mapsManagerQueryOptions.mapRotation(),
    initialData: loaderData.rotation,
    refetchOnMount: false,
  });

  useEffect(() => {
    setDraftShuffle(shuffleEnabled);
  }, [shuffleEnabled]);

  const hasChanges = draftShuffle !== shuffleEnabled;
  const previewMaps = useMemo(
    () => (rotation?.maps ?? []).slice(0, 5),
    [rotation]
  );

  const { mutate: saveShuffle, isPending } = useMutation({
    ...mapsManagerMutationOptions.setMapRotationShuffle,
    onSuccess: (response) => {
      const enabled = response.arguments.enabled;
      queryClient.setQueryData(
        mapsManagerQueryKeys.mapRotationShuffle,
        enabled
      );
      queryClient.invalidateQueries({
        queryKey: mapsManagerQueryKeys.mapRotationShuffle,
      });
      toast.success(
        t("maps.rotationShuffleUpdated", {
          state: t(enabled ? "common.enabled" : "common.disabled"),
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

  return (
    <>
      <Box sx={{ p: { xs: 1.5, md: 2.5 }, pb: 0 }}>
        <Stack spacing={1.5}>
          <Box data-theme-surface="panel"
            component="section"
            sx={{ border: "1px solid", borderColor: "divider" }}
          >
            <Stack
              direction={{ xs: "column", md: "row" }}
              justifyContent="space-between"
              alignItems={{ xs: "stretch", md: "center" }}
              gap={1.5}
              sx={{ p: 2, borderBottom: "1px solid", borderColor: "divider" }}
            >
              <Box>
                <Typography
                  variant="overline"
                  color="primary.main"
                  sx={{ display: "block" }}
                >
                  {t("maps.rotationWorkbench.behaviorEyebrow")}
                </Typography>
                <Typography component="h2" variant="h6" fontWeight={850}>
                  {t("maps.rotationWorkbench.behaviorTitle")}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t("maps.rotationWorkbench.behaviorDescription")}
                </Typography>
              </Box>
              <FormControlLabel
                labelPlacement="start"
                control={
                  <Switch
                    checked={draftShuffle}
                    onChange={(event) => setDraftShuffle(event.target.checked)}
                    disabled={isPending}
                    inputProps={{
                      "aria-label": t("maps.rotationShuffle"),
                    }}
                  />
                }
                label={
                  <Stack sx={{ mr: 1 }}>
                    <Typography variant="body2" fontWeight={800}>
                      {t("maps.rotationShuffle")}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {draftShuffle
                        ? t("maps.rotationWorkbench.shuffleActive")
                        : t("maps.rotationWorkbench.shuffleInactive")}
                    </Typography>
                  </Stack>
                }
                sx={{ m: 0, justifyContent: "space-between" }}
              />
            </Stack>

            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" },
              }}
            >
              <SummaryMetric
                label={t("maps.rotationWorkbench.mode")}
                value={
                  draftShuffle
                    ? t("maps.rotationWorkbench.random")
                    : t("maps.rotationWorkbench.fixed")
                }
                detail={t("maps.rotationWorkbench.modeDetail")}
                icon={<ShuffleOutlinedIcon />}
              />
              <SummaryMetric
                label={t("maps.rotationWorkbench.rotationSize")}
                value={t("maps.rotationWorkbench.mapsCount", {
                  count: rotation?.maps?.length ?? 0,
                })}
                detail={t("maps.rotationWorkbench.rotationSizeDetail")}
                icon={<AutorenewOutlinedIcon />}
              />
              <SummaryMetric
                label={t("maps.rotationWorkbench.preview")}
                value={t("maps.rotationWorkbench.mapsCount", {
                  count: previewMaps.length,
                })}
                detail={t("maps.rotationWorkbench.previewDetail")}
                icon={<CheckCircleOutlineIcon />}
              />
            </Box>
          </Box>

          <Box data-theme-surface="panel"
            component="section"
            sx={{ border: "1px solid", borderColor: "divider" }}
          >
            <Box
              sx={{
                px: 2,
                py: 1.5,
                borderBottom: "1px solid",
                borderColor: "divider",
                bgcolor: "background.default",
              }}
            >
              <Typography component="h2" variant="h6" fontWeight={850}>
                {t("maps.rotationWorkbench.nextFiveTitle")}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {draftShuffle
                  ? t("maps.rotationWorkbench.nextFiveShuffleDescription")
                  : t("maps.rotationWorkbench.nextFiveDescription")}
              </Typography>
            </Box>
            {previewMaps.length ? (
              <Box component="ol" sx={{ p: 0, m: 0, listStyle: "none" }}>
                {previewMaps.map((mapLayer, index) => (
                  <PreviewRow
                    key={`${mapLayer.id}-${index}`}
                    mapLayer={mapLayer}
                    index={index}
                  />
                ))}
              </Box>
            ) : (
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ p: 3, textAlign: "center" }}
              >
                {t("maps.rotationWorkbench.noPreview")}
              </Typography>
            )}
          </Box>
        </Stack>
      </Box>

      <ConfigActionBar
        mobileSticky={false}
        dirty={hasChanges}
        dirtyLabel={t("maps.rotationWorkbench.unsavedChanges")}
        stateIcon={
          hasChanges ? (
            <ReplayIcon color="warning" fontSize="small" />
          ) : (
            <CheckCircleOutlineIcon color="success" fontSize="small" />
          )
        }
        stateLabel={
          hasChanges
            ? t("maps.rotationWorkbench.settingsChangesPending")
            : t("maps.rotationWorkbench.settingsSaved")
        }
        stateDescription={t("maps.rotationWorkbench.settingsStateDescription")}
        secondaryActions={[
          {
            id: "reset-rotation-settings",
            label: t("maps.resetChanges"),
            startIcon: <ReplayIcon />,
            disabled: !hasChanges || isPending,
            onClick: () => setDraftShuffle(shuffleEnabled),
          },
        ]}
        primaryAction={{
          label: t("maps.rotationWorkbench.saveSettings"),
          loadingLabel: t("common.loading"),
          startIcon: isPending ? <CircularProgress size={18} /> : <SaveIcon />,
          disabled: !hasChanges || isPending,
          loading: isPending,
          onClick: () => saveShuffle(draftShuffle),
        }}
      />
    </>
  );
}

export default MapRotationSettings;
