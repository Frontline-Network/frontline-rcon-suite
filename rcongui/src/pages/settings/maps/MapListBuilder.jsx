import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Badge,
  Box,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import MapOutlinedIcon from "@mui/icons-material/MapOutlined";
import ReplayIcon from "@mui/icons-material/Replay";
import SaveIcon from "@mui/icons-material/Save";
import uniqBy from "lodash/uniqBy";
import { useTranslation } from "react-i18next";
import ConfigActionBar from "@/pages/settings/config-form/ConfigActionBar";
import { MapFilter } from "./MapFilter";
import { MapList } from "./MapList";

const withSelectionId = (mapLayer) => ({
  ...mapLayer,
  selectionId: `${mapLayer.id}-${Math.random().toString(36).slice(2, 9)}`,
});

const orderedIds = (maps = []) => maps.map((map) => map.id);
const sameOrder = (left = [], right = []) =>
  left.length === right.length && left.every((id, index) => id === right[index]);

function BuilderPanel({ title, description, count, children, testId }) {
  return (
    <Box
      component="section"
      data-testid={testId}
      sx={{
        border: "1px solid",
        borderColor: "divider",
        minWidth: 0,
        height: "100%",
        bgcolor: "background.paper",
      }}
    >
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        gap={1}
        sx={{
          minHeight: 68,
          px: 2,
          py: 1.25,
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
            {description}
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

/**
 * Draft/publish workspace used by both the server rotation and the optional
 * one-off sequence. The backend payload remains an ordered list of map IDs.
 */
export function MapListBuilder({
  maps: allMaps = [],
  slots = {},
  selectedMaps = [],
  onSave,
  isSaveDisabled,
  isSaving,
  exclusive = false,
  actions,
  params = {},
  selectedMapListProps = {},
}) {
  const { t } = useTranslation();
  const theme = useTheme();
  const mobile = useMediaQuery(theme.breakpoints.down("md"));
  const persistedIds = useMemo(() => orderedIds(selectedMaps), [selectedMaps]);
  const [mapSelection, setMapSelection] = useState(
    selectedMaps.map(withSelectionId)
  );
  const [filteredMapOptions, setFilteredMapOptions] = useState(allMaps);
  const [view, setView] = useState("catalog");

  useEffect(() => {
    setMapSelection(selectedMaps.map(withSelectionId));
  }, [selectedMaps]);

  const mapOptions = useMemo(() => {
    if (!exclusive) return allMaps;
    const selectedIds = new Set(mapSelection.map((map) => map.id));
    return allMaps.filter((map) => !selectedIds.has(map.id));
  }, [allMaps, exclusive, mapSelection]);

  useEffect(() => {
    setFilteredMapOptions(mapOptions);
  }, [mapOptions]);

  const handleFilterChange = useCallback((filteredMaps) => {
    setFilteredMapOptions(filteredMaps);
  }, []);

  const currentIds = useMemo(() => orderedIds(mapSelection), [mapSelection]);
  const hasChanges = !sameOrder(currentIds, persistedIds);
  const duplicateCount = currentIds.length - new Set(currentIds).size;

  const addSelectionItem = useCallback(
    (mapLayer) => {
      setMapSelection((current) =>
        exclusive
          ? uniqBy([...current, withSelectionId(mapLayer)], "id")
          : [...current, withSelectionId(mapLayer)]
      );
    },
    [exclusive]
  );

  const removeSelectedItem = useCallback((mapItem) => {
    setMapSelection((current) =>
      current.filter((item) => item.selectionId !== mapItem.selectionId)
    );
  }, []);

  const resetSelection = () =>
    setMapSelection(selectedMaps.map(withSelectionId));
  const clearSelection = () => setMapSelection([]);
  const saveSelection = () => onSave(currentIds);

  const selectionTitle =
    selectedMapListProps.title || t("maps.rotationWorkbench.draftTitle");
  const selectionDescription =
    selectedMapListProps.description ||
    t("maps.rotationWorkbench.draftDescription");
  const saveLabel =
    selectedMapListProps.saveLabel || t("maps.rotationWorkbench.publish");
  const stateDescription = duplicateCount
    ? t("maps.rotationWorkbench.duplicateNotice", { count: duplicateCount })
    : t("maps.rotationWorkbench.draftState", {
        count: mapSelection.length,
      });

  return (
    <>
      <Box sx={{ p: { xs: 1.5, md: 2.5 }, pb: 0 }}>
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
                minHeight: 44,
                minWidth: 0,
                px: 1,
                flex: 1,
              },
            }}
          >
            <ToggleButton value="catalog">
              {t("maps.rotationWorkbench.catalogTab")}
            </ToggleButton>
            <ToggleButton value="draft">
              {t("maps.rotationWorkbench.draftTab")}
              <Badge
                color="primary"
                showZero
                badgeContent={mapSelection.length}
                sx={{ ml: 1.5 }}
              />
            </ToggleButton>
          </ToggleButtonGroup>
        )}

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "minmax(0, 1fr)", md: "minmax(0, 5fr) minmax(0, 7fr)" },
            gap: 1.5,
            alignItems: "stretch",
            minWidth: 0,
          }}
        >
          {(!mobile || view === "catalog") && (
            <Box sx={{ minWidth: 0 }}>
              <BuilderPanel
                testId="rotation-map-catalog"
                title={t("maps.rotationWorkbench.catalogTitle")}
                description={t("maps.rotationWorkbench.catalogDescription")}
                count={filteredMapOptions.length}
              >
                <MapFilter
                  maps={mapOptions}
                  onFilterChange={handleFilterChange}
                  compact
                />
                <Box
                  sx={{
                    maxHeight: { xs: "none", md: 580 },
                    overflowY: { xs: "visible", md: "auto" },
                    scrollbarWidth: "thin",
                    p: 1,
                  }}
                >
                  <MapList
                    maps={filteredMapOptions}
                    emptyListMessage={t("maps.noMoreMaps")}
                    renderItem={(mapLayer) => (
                      <slots.MapListItem
                        key={mapLayer.id}
                        mapLayer={mapLayer}
                        onClick={addSelectionItem}
                      />
                    )}
                  />
                </Box>
              </BuilderPanel>
            </Box>
          )}

          {(!mobile || view === "draft") && (
            <Box sx={{ minWidth: 0 }}>
              <BuilderPanel
                testId="rotation-map-draft"
                title={selectionTitle}
                description={selectionDescription}
                count={mapSelection.length}
              >
                <slots.SelectedMapList
                  maps={mapSelection}
                  onRemove={removeSelectedItem}
                  onClear={clearSelection}
                  setMaps={setMapSelection}
                  onReset={resetSelection}
                  onSave={saveSelection}
                  isDisabled={isSaveDisabled}
                  isSaving={isSaving}
                  actions={actions}
                  params={params}
                  {...selectedMapListProps}
                />
              </BuilderPanel>
            </Box>
          )}
        </Box>

        {mapSelection.length === 0 && (
          <Stack
            direction="row"
            spacing={1}
            alignItems="center"
            role="status"
            sx={{
              mt: 1.5,
              p: 1.5,
              border: "1px solid",
              borderColor: "warning.dark",
              bgcolor: "rgba(214, 170, 77, 0.08)",
            }}
          >
            <MapOutlinedIcon color="warning" fontSize="small" />
            <Typography variant="body2">
              {t("maps.rotationWorkbench.emptyDraftNotice")}
            </Typography>
          </Stack>
        )}
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
            ? t("maps.rotationWorkbench.changesPending")
            : t("maps.rotationWorkbench.saved")
        }
        stateDescription={stateDescription}
        secondaryActions={[
          {
            id: "reset-map-draft",
            label: t("maps.resetChanges"),
            startIcon: <ReplayIcon />,
            disabled: !hasChanges || isSaving,
            onClick: resetSelection,
          },
        ]}
        primaryAction={{
          label: saveLabel,
          loadingLabel: t("common.loading"),
          startIcon: <SaveIcon />,
          disabled: !hasChanges || isSaving || isSaveDisabled,
          loading: isSaving,
          onClick: saveSelection,
        }}
      />
    </>
  );
}

export default MapListBuilder;
