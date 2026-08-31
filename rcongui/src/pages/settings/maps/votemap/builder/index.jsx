import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLoaderData } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Box,
  Button,
  CircularProgress,
  FormControl,
  InputLabel,
  InputAdornment,
  LinearProgress,
  MenuItem,
  Select,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import BallotOutlinedIcon from "@mui/icons-material/BallotOutlined";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import CloseIcon from "@mui/icons-material/Close";
import FilterAltOutlinedIcon from "@mui/icons-material/FilterAltOutlined";
import ReplayIcon from "@mui/icons-material/Replay";
import RestoreIcon from "@mui/icons-material/Restore";
import SaveIcon from "@mui/icons-material/Save";
import SearchOutlinedIcon from "@mui/icons-material/SearchOutlined";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import { toast } from "react-toastify";
import { useTranslation } from "react-i18next";
import ConfirmButton from "@/components/shared/ConfirmButton";
import { useAuth } from "@/hooks/useAuth";
import { isFakeMode } from "@/mirage/demo-data";
import { getMapEnvironmentLabel, getMapModeLabel } from "@/utils/mapLabels";
import ConfigActionBar from "@/pages/settings/config-form/ConfigActionBar";
import {
  getMapLayerImageSrc,
  unifiedGamemodeName,
} from "../../objectives/helpers";
import {
  mapsManagerMutationOptions,
  mapsManagerQueryKeys,
  mapsManagerQueryOptions,
} from "../../queries";

const sameIdSet = (left = [], right = []) =>
  left.length === right.length &&
  new Set(left).size === new Set(right).size &&
  left.every((id) => right.includes(id));

function MapPoolRow({ mapLayer, action, selected = false }) {
  const { t } = useTranslation();
  const mode = unifiedGamemodeName(mapLayer.game_mode);

  return (
    <Box
      component="article"
      sx={{
        display: "grid",
        gridTemplateColumns: "88px minmax(0, 1fr) auto",
        minHeight: 62,
        alignItems: "stretch",
        borderBottom: "1px solid",
        borderColor: "divider",
        bgcolor: selected ? "action.selected" : "transparent",
        "&:hover": { bgcolor: "action.hover" },
      }}
    >
      <Box
        component="img"
        src={getMapLayerImageSrc(mapLayer)}
        alt=""
        sx={{ width: 88, height: "100%", minHeight: 62, objectFit: "cover" }}
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
      <Box sx={{ display: "grid", placeItems: "center", px: 1 }}>{action}</Box>
    </Box>
  );
}

function PoolPanel({ title, subtitle, count, children, testId }) {
  return (
    <Box
      component="section"
      data-testid={testId}
      sx={{ border: "1px solid", borderColor: "divider", minWidth: 0 }}
    >
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{
          px: 2,
          py: 1.5,
          borderBottom: "1px solid",
          borderColor: "divider",
          bgcolor: "background.default",
        }}
      >
        <Box sx={{ minWidth: 0 }}>
          <Typography component="h2" variant="h6" fontWeight={850}>
            {title}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {subtitle}
          </Typography>
        </Box>
        <Typography variant="overline" color="primary.main">
          {count}
        </Typography>
      </Stack>
      {children}
    </Box>
  );
}

export default function VotemapBuilderPage() {
  const { t } = useTranslation();
  const loaderData = useLoaderData();
  const { maps = [] } = loaderData;
  const queryClient = useQueryClient();
  const theme = useTheme();
  const mobile = useMediaQuery(theme.breakpoints.down("md"));
  const { permissions } = useAuth();
  const fakeMode = isFakeMode();
  const [view, setView] = useState("available");
  const [search, setSearch] = useState("");
  const [mode, setMode] = useState("all");
  const [environment, setEnvironment] = useState("all");
  const [draftIds, setDraftIds] = useState(loaderData.whitelist ?? []);
  const previousServerIds = useRef(loaderData.whitelist ?? []);

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

  const { data: whitelist = [], isLoading: isLoadingWhitelist } = useQuery({
    ...mapsManagerQueryOptions.votemapWhitelist(),
    initialData: loaderData.whitelist,
    staleTime: 5_000,
    refetchOnMount: false,
  });

  const hasChanges = useMemo(
    () => !sameIdSet(draftIds, whitelist),
    [draftIds, whitelist]
  );

  useEffect(() => {
    setDraftIds((current) =>
      sameIdSet(current, previousServerIds.current) ? whitelist : current
    );
    previousServerIds.current = whitelist;
  }, [whitelist]);

  const selectedSet = useMemo(() => new Set(draftIds), [draftIds]);
  const selectedMaps = useMemo(
    () =>
      draftIds.map((id) => maps.find((map) => map.id === id)).filter(Boolean),
    [draftIds, maps]
  );
  const modes = useMemo(
    () =>
      Array.from(
        new Set(maps.map((map) => unifiedGamemodeName(map.game_mode)))
      ).sort(),
    [maps]
  );
  const environments = useMemo(
    () => Array.from(new Set(maps.map((map) => map.environment))).sort(),
    [maps]
  );
  const availableMaps = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return maps.filter((map) => {
      if (selectedSet.has(map.id)) return false;
      if (
        normalizedSearch &&
        !`${map.map.pretty_name} ${map.id}`
          .toLowerCase()
          .includes(normalizedSearch)
      ) {
        return false;
      }
      if (mode !== "all" && unifiedGamemodeName(map.game_mode) !== mode)
        return false;
      if (environment !== "all" && map.environment !== environment)
        return false;
      return true;
    });
  }, [environment, maps, mode, search, selectedSet]);

  const invalidMapIds = useMemo(
    () => draftIds.filter((id) => !maps.some((map) => map.id === id)),
    [draftIds, maps]
  );
  const emptyPool = draftIds.length === 0;

  useEffect(() => {
    if (invalidMapIds.length) {
      toast.error(
        t("maps.votemapWhitelistOutdated", { maps: invalidMapIds.join(", ") })
      );
    }
  }, [invalidMapIds, t]);

  const { mutate: saveWhitelist, isPending: isSaving } = useMutation({
    mutationFn: fakeMode
      ? async (mapIds) => ({ arguments: { map_names: mapIds } })
      : mapsManagerMutationOptions.setWhitelist.mutationFn,
    onSuccess: (response, submittedIds) => {
      const savedIds = response?.arguments?.map_names ?? submittedIds;
      previousServerIds.current = savedIds;
      setDraftIds(savedIds);
      queryClient.setQueryData(mapsManagerQueryKeys.votemapWhitelist, savedIds);
      if (!fakeMode) {
        queryClient.invalidateQueries({
          queryKey: mapsManagerQueryKeys.votemapWhitelist,
        });
      }
      toast.success(t("maps.votemapWhitelistSaved"));
    },
    onError: (error) => toast.error(`${error.name}: ${error.message}`),
  });

  const { mutate: resetWhitelist, isPending: isResetting } = useMutation({
    mutationFn: fakeMode
      ? async () => ({ arguments: { map_names: maps.map((map) => map.id) } })
      : mapsManagerMutationOptions.resetVotemapWhitelist.mutationFn,
    onSuccess: async (response) => {
      let resetIds;
      if (fakeMode) {
        resetIds = response?.arguments?.map_names ?? [];
        queryClient.setQueryData(
          mapsManagerQueryKeys.votemapWhitelist,
          resetIds
        );
      } else {
        await queryClient.invalidateQueries({
          queryKey: mapsManagerQueryKeys.votemapWhitelist,
        });
        resetIds =
          queryClient.getQueryData(mapsManagerQueryKeys.votemapWhitelist) ?? [];
      }
      previousServerIds.current = resetIds;
      setDraftIds(resetIds);
      toast.success(t("maps.votemapWhitelistReset"));
    },
    onError: (error) => toast.error(`${error.name}: ${error.message}`),
  });

  const addMap = useCallback((id) => {
    setDraftIds((current) =>
      current.includes(id) ? current : [...current, id]
    );
  }, []);
  const removeMap = useCallback((id) => {
    setDraftIds((current) => current.filter((currentId) => currentId !== id));
  }, []);

  return (
    <>
      {isLoadingWhitelist && <LinearProgress />}
      <Box
        sx={{
          width: "100%",
          minWidth: 0,
          boxSizing: "border-box",
          p: { xs: 1.5, md: 2.5 },
          pb: 1.5,
        }}
      >
        <Stack
          direction={{ xs: "column", md: "row" }}
          justifyContent="space-between"
          gap={1.5}
          sx={{ mb: 2 }}
        >
          <Box>
            <Typography variant="overline" color="primary.main">
              {t("maps.votemapWorkbench.poolEyebrow")}
            </Typography>
            <Typography component="h2" variant="h5" fontWeight={850}>
              {t("maps.votemapWorkbench.poolTitle")}
            </Typography>
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ mt: 0.35 }}
            >
              {t("maps.votemapWorkbench.poolDescription")}
            </Typography>
          </Box>
          <Stack direction="row" spacing={1} alignItems="center">
            <BallotOutlinedIcon color="primary" />
            <Box>
              <Typography variant="overline" color="text.secondary">
                {t("maps.votemapWorkbench.poolSize")}
              </Typography>
              <Typography variant="body1" fontWeight={850}>
                {t("maps.votemapWorkbench.mapsSelected", {
                  count: draftIds.length,
                })}
              </Typography>
            </Box>
          </Stack>
        </Stack>

        {mobile && (
          <ToggleButtonGroup
            value={view}
            exclusive
            onChange={(_, next) => next && setView(next)}
            fullWidth
            aria-label={t("maps.mobileView")}
            sx={{
              mb: 1.5,
              "& .MuiToggleButton-root": {
                minWidth: 0,
                minHeight: 44,
                px: 1,
              },
            }}
          >
            <ToggleButton value="available">
              {t("maps.votemapWorkbench.availableMaps", {
                count: availableMaps.length,
              })}
            </ToggleButton>
            <ToggleButton value="pool">
              {t("maps.votemapWorkbench.activePool", {
                count: draftIds.length,
              })}
            </ToggleButton>
          </ToggleButtonGroup>
        )}

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              md: "minmax(0, 0.9fr) minmax(0, 1.1fr)",
            },
            gap: 1.5,
            minWidth: 0,
          }}
        >
          {(!mobile || view === "available") && (
            <PoolPanel
              testId="votemap-available-maps"
              title={t("maps.votemapWorkbench.availableTitle")}
              subtitle={t("maps.votemapWorkbench.availableDescription")}
              count={availableMaps.length}
            >
              <Box
                sx={{
                  p: 1.5,
                  borderBottom: "1px solid",
                  borderColor: "divider",
                }}
              >
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
                    gap: 1,
                  }}
                >
                  <TextField
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    label={t("maps.votemapWorkbench.searchMaps")}
                    size="small"
                    fullWidth
                    sx={{
                      gridColumn: "1 / -1",
                      "& .MuiInputBase-root": { minHeight: 44 },
                    }}
                    slotProps={{
                      input: {
                        startAdornment: (
                          <InputAdornment position="start">
                            <SearchOutlinedIcon fontSize="small" />
                          </InputAdornment>
                        ),
                      },
                    }}
                  />
                  <FormControl
                    size="small"
                    fullWidth
                    sx={{ "& .MuiInputBase-root": { minHeight: 44 } }}
                  >
                    <InputLabel id="votemap-map-mode-label">
                      {t("maps.gameMode")}
                    </InputLabel>
                    <Select
                      value={mode}
                      label={t("maps.gameMode")}
                      labelId="votemap-map-mode-label"
                      onChange={(event) => setMode(event.target.value)}
                    >
                      <MenuItem value="all">
                        {t("maps.votemapWorkbench.allModes")}
                      </MenuItem>
                      {modes.map((value) => (
                        <MenuItem key={value} value={value}>
                          {getMapModeLabel(t, value)}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  <FormControl
                    size="small"
                    fullWidth
                    sx={{ "& .MuiInputBase-root": { minHeight: 44 } }}
                  >
                    <InputLabel id="votemap-map-environment-label">
                      {t("maps.weather")}
                    </InputLabel>
                    <Select
                      value={environment}
                      label={t("maps.weather")}
                      labelId="votemap-map-environment-label"
                      onChange={(event) => setEnvironment(event.target.value)}
                    >
                      <MenuItem value="all">
                        {t("maps.votemapWorkbench.allEnvironments")}
                      </MenuItem>
                      {environments.map((value) => (
                        <MenuItem key={value} value={value}>
                          {getMapEnvironmentLabel(t, value)}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Box>
              </Box>

              <Box
                sx={{
                  maxHeight: { xs: "none", md: 580 },
                  overflowY: { xs: "visible", md: "auto" },
                  scrollbarWidth: "thin",
                }}
              >
                {availableMaps.length ? (
                  availableMaps.map((mapLayer) => (
                    <MapPoolRow
                      key={mapLayer.id}
                      mapLayer={mapLayer}
                      action={
                        <Button
                          variant="text"
                          color="success"
                          aria-label={t("maps.votemapWorkbench.addMap", {
                            map: mapLayer.map.pretty_name,
                          })}
                          disabled={isSaving || isResetting}
                          onClick={() => addMap(mapLayer.id)}
                          startIcon={<AddIcon />}
                          sx={{ minHeight: 44, minWidth: 44 }}
                        >
                          <Box
                            component="span"
                            sx={{ display: { xs: "none", xl: "inline" } }}
                          >
                            {t("maps.add")}
                          </Box>
                        </Button>
                      }
                    />
                  ))
                ) : (
                  <Stack
                    alignItems="center"
                    spacing={1}
                    sx={{ py: 7, px: 2, textAlign: "center" }}
                  >
                    <FilterAltOutlinedIcon
                      sx={{ fontSize: 42, color: "text.disabled" }}
                    />
                    <Typography variant="h6">{t("maps.noMaps")}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {t("maps.adjustFilters")}
                    </Typography>
                  </Stack>
                )}
              </Box>
            </PoolPanel>
          )}

          {(!mobile || view === "pool") && (
            <PoolPanel
              testId="votemap-selected-pool"
              title={t("maps.votemapWorkbench.activePoolTitle")}
              subtitle={t("maps.votemapWorkbench.activePoolDescription")}
              count={draftIds.length}
            >
              <Box
                sx={{
                  maxHeight: { xs: "none", md: 580 },
                  overflowY: { xs: "visible", md: "auto" },
                  scrollbarWidth: "thin",
                }}
              >
                {invalidMapIds.map((id) => (
                  <Stack
                    key={id}
                    component="article"
                    direction="row"
                    alignItems="center"
                    justifyContent="space-between"
                    gap={1}
                    sx={{
                      minHeight: 62,
                      px: 1.5,
                      borderBottom: "1px solid",
                      borderColor: "warning.dark",
                      bgcolor: "rgba(214, 170, 77, 0.08)",
                    }}
                  >
                    <Box sx={{ minWidth: 0 }}>
                      <Stack direction="row" spacing={1} alignItems="center">
                        <WarningAmberOutlinedIcon
                          color="warning"
                          fontSize="small"
                        />
                        <Typography variant="body2" fontWeight={800} noWrap>
                          {id}
                        </Typography>
                      </Stack>
                      <Typography variant="caption" color="text.secondary">
                        {t("maps.votemapWorkbench.invalidMapDescription")}
                      </Typography>
                    </Box>
                    <Button
                      variant="text"
                      color="error"
                      aria-label={t("maps.votemapWorkbench.removeInvalidMap", {
                        map: id,
                      })}
                      disabled={isSaving || isResetting}
                      onClick={() => removeMap(id)}
                      sx={{ minWidth: 44, width: 44, height: 44, p: 0 }}
                    >
                      <CloseIcon fontSize="small" />
                    </Button>
                  </Stack>
                ))}
                {selectedMaps.length ? (
                  selectedMaps.map((mapLayer) => (
                    <MapPoolRow
                      key={mapLayer.id}
                      mapLayer={mapLayer}
                      action={
                        <Button
                          variant="text"
                          color="error"
                          aria-label={t("maps.votemapWorkbench.removeMap", {
                            map: mapLayer.map.pretty_name,
                          })}
                          disabled={isSaving || isResetting}
                          onClick={() => removeMap(mapLayer.id)}
                          sx={{ minWidth: 44, width: 44, height: 44, p: 0 }}
                        >
                          <CloseIcon fontSize="small" />
                        </Button>
                      }
                    />
                  ))
                ) : invalidMapIds.length === 0 ? (
                  <Stack
                    alignItems="center"
                    spacing={1}
                    sx={{ py: 7, px: 2, textAlign: "center" }}
                  >
                    <BallotOutlinedIcon
                      sx={{ fontSize: 42, color: "text.disabled" }}
                    />
                    <Typography variant="h6">
                      {t("maps.votemapWorkbench.emptyPool")}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {t("maps.votemapWorkbench.emptyPoolDescription")}
                    </Typography>
                  </Stack>
                ) : null}
              </Box>
            </PoolPanel>
          )}
        </Box>

        {emptyPool && (
          <Stack
            direction="row"
            spacing={1}
            alignItems="center"
            role="alert"
            sx={{
              mt: 1.5,
              p: 1.5,
              border: "1px solid",
              borderColor: "error.dark",
              bgcolor: "rgba(211, 81, 81, 0.08)",
            }}
          >
            <WarningAmberOutlinedIcon color="error" fontSize="small" />
            <Typography variant="body2">
              {t("maps.votemapWorkbench.poolRequiresMap")}
            </Typography>
          </Stack>
        )}
      </Box>

      <ConfigActionBar
        mobileSticky={false}
        dirty={hasChanges}
        dirtyLabel={t("maps.votemapWorkbench.unsavedChanges")}
        stateIcon={
          hasChanges ? (
            <ReplayIcon color="warning" fontSize="small" />
          ) : (
            <CheckCircleOutlineIcon color="success" fontSize="small" />
          )
        }
        stateLabel={
          hasChanges
            ? t("maps.votemapWorkbench.poolChangesPending")
            : t("maps.votemapWorkbench.poolSaved")
        }
        stateDescription={t("maps.votemapWorkbench.poolStateDescription", {
          count: draftIds.length,
        })}
        secondaryActions={[
          {
            id: "restore-votemap-pool",
            label: t("maps.resetChanges"),
            startIcon: <ReplayIcon />,
            disabled: !hasChanges || isSaving || isResetting,
            onClick: () => setDraftIds(whitelist),
          },
          {
            id: "reset-votemap-pool",
            node: (
              <ConfirmButton
                key="reset-votemap-pool"
                disabled={
                  isSaving || isResetting || !can("can_reset_map_whitelist")
                }
                onConfirm={resetWhitelist}
                title={t("maps.votemapWorkbench.resetPoolTitle")}
                description={t("maps.votemapWorkbench.resetPoolDescription")}
                buttonText={t("maps.votemapWorkbench.restoreAllMaps")}
                buttonProps={{
                  variant: "outlined",
                  color: "warning",
                  startIcon: <RestoreIcon />,
                }}
              />
            ),
          },
        ]}
        primaryAction={{
          label: t("maps.votemapWorkbench.savePool"),
          loadingLabel: t("common.loading"),
          startIcon: isSaving ? <CircularProgress size={18} /> : <SaveIcon />,
          disabled:
            !hasChanges ||
            isSaving ||
            isResetting ||
            emptyPool ||
            invalidMapIds.length > 0 ||
            !can("can_set_map_whitelist"),
          loading: isSaving,
          onClick: () => saveWhitelist(draftIds),
        }}
      />
    </>
  );
}
