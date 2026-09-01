import { useEffect, useState } from "react";
import { useLoaderData } from "react-router-dom";
import {
  Box,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  FormControl,
  FormControlLabel,
  FormGroup,
  FormLabel,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import FormatListNumberedIcon from "@mui/icons-material/FormatListNumbered";
import MapOutlinedIcon from "@mui/icons-material/MapOutlined";
import RestartAltOutlinedIcon from "@mui/icons-material/RestartAltOutlined";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "react-toastify";
import { useTranslation } from "react-i18next";
import PageHeader from "@/components/shared/PageHeader";
import PageState from "@/components/shared/PageState";
import { useGlobalStore } from "@/stores/global-state";
import { MapObjectivesPicker } from "./MapObjectivesPicker";
import {
  flip,
  generateObjectivesGrid,
  getSelectedObjectives,
  reduceToInts,
  unifiedGamemodeName,
} from "./helpers";
import {
  mapsManagerMutationOptions,
  mapsManagerQueryOptions,
} from "../queries";

function SectionHeader({ eyebrow, title, description, action }) {
  return (
    <Stack
      direction="row"
      justifyContent="space-between"
      alignItems="flex-start"
      gap={1.5}
      sx={{ px: { xs: 1.5, sm: 2 }, py: 1.5 }}
    >
      <Box sx={{ minWidth: 0 }}>
        <Typography variant="overline" color="primary.main">
          {eyebrow}
        </Typography>
        <Typography component="h2" variant="h6" fontWeight={850}>
          {title}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
          {description}
        </Typography>
      </Box>
      {action}
    </Stack>
  );
}

function ImpactMetric({ label, value }) {
  return (
    <Box sx={{ minWidth: 0, px: 1.5, py: 1.25 }}>
      <Typography variant="overline" color="text.secondary">
        {label}
      </Typography>
      <Typography
        variant="body2"
        fontWeight={850}
        sx={{ overflowWrap: "anywhere" }}
      >
        {value}
      </Typography>
    </Box>
  );
}

function MapObjectivesPage() {
  const { t } = useTranslation();
  const initialData = useLoaderData();
  const theme = useTheme();
  const mobile = useMediaQuery(theme.breakpoints.down("md"));
  const sectorLayout = initialData.sectorLayout || {
    read: true,
    set: true,
    remove: false,
  };
  const [currentMap, setCurrentMap] = useState(
    initialData.gameState.current_map
  );
  const [objectives, setObjectives] = useState(
    generateObjectivesGrid(initialData.gameState.current_map.map.orientation)
  );
  const [randomConstraint, setRandomConstraint] = useState({
    1: true,
    2: false,
  });
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [mobileView, setMobileView] = useState("map");
  const serverState = useGlobalStore((state) => state.serverState);
  const status = useGlobalStore((state) => state.status);
  const gameState = useGlobalStore((state) => state.gameState);

  const { data: objectiveNames, refetch: refetchObjectiveNames } = useQuery({
    ...mapsManagerQueryOptions.objectives(),
    initialData: initialData.objectives,
    enabled: sectorLayout.read,
  });
  const mapOrientation = currentMap.map.orientation;
  const selectedObjectives = objectiveNames
    ? getSelectedObjectives(objectives, objectiveNames, mapOrientation)
    : [];
  const selectedCount = objectives
    .flat()
    .filter((value) => value === true).length;
  const randomCount = Math.max(0, 5 - selectedCount);

  const { refetch: refetchGameState } = useQuery({
    ...mapsManagerQueryOptions.gameState(),
    enabled: false,
  });

  const { mutate: changeObjectives, isPending: objectivesChanging } =
    useMutation({
      ...mapsManagerMutationOptions.changeObjectives,
      onSuccess: (response) => {
        const newObjectives = response.result;
        const finalObjectives = generateObjectivesGrid(mapOrientation);
        const isHorizontal = mapOrientation === "horizontal";
        newObjectives.forEach((objective, rowIndex) => {
          const col = objectiveNames[rowIndex].indexOf(objective);
          if (isHorizontal) finalObjectives[col + 1][rowIndex] = true;
          else finalObjectives[rowIndex][col + 1] = true;
        });
        setObjectives(finalObjectives);
        toast.success(t("maps.objectivesChanged"));
        setConfirmDialogOpen(false);
      },
      onError: (error) => {
        toast.error(`${error.name}: ${error.message}`);
        setConfirmDialogOpen(false);
      },
    });

  const handleConstraintChange = (event) => {
    setRandomConstraint((current) => ({
      ...current,
      [event.target.name]: event.target.checked,
    }));
  };

  const handleObjectiveClick = (index) => {
    const targetIndex = index % 5;
    const targetRow = Math.floor(index / 5);
    setObjectives((current) =>
      current.map((row, rowIndex) =>
        row.map((item, itemIndex) =>
          rowIndex === targetRow && itemIndex === targetIndex ? !item : item
        )
      )
    );
  };

  const handleObjectiveNamePick = (row, index) => {
    const targetRow = mapOrientation === "vertical" ? row : index + 1;
    const targetCol = mapOrientation === "vertical" ? index + 1 : row;
    setObjectives((current) =>
      current.map((objectiveRow, rowIndex) =>
        objectiveRow.map((item, colIndex) => {
          if (item === null) return null;
          if (mapOrientation === "vertical" && rowIndex === targetRow) {
            return colIndex === targetCol;
          }
          if (mapOrientation !== "vertical" && colIndex === targetCol) {
            return rowIndex === targetRow;
          }
          return item;
        })
      )
    );
  };

  const handleClearClick = () => {
    setObjectives(generateObjectivesGrid(currentMap.map.orientation));
  };

  const handleDialogConfirmationClick = async () => {
    await refetchGameState();
    const chosenObjectives = reduceToInts(
      objectives[1][0] !== null ? flip(objectives) : objectives
    );
    const constraintValue = Object.entries(randomConstraint).reduce(
      (sum, [value, used]) => (used ? sum + Number(value) : sum),
      0
    );
    changeObjectives({
      objectives: chosenObjectives,
      random_constraints: constraintValue,
    });
  };

  useEffect(() => {
    if (!sectorLayout.read) return;
    const global = gameState?.current_map;
    if (!global || currentMap.id === global.id) return;
    toast.info(
      `${t("maps.mapChanged")}: ${currentMap.pretty_name} → ${
        global.pretty_name
      }`
    );
    setCurrentMap(global);
    setObjectives(generateObjectivesGrid(global.map.orientation));
    setConfirmDialogOpen(false);
    refetchObjectiveNames();
  }, [
    currentMap,
    gameState?.current_map,
    refetchObjectiveNames,
    sectorLayout.read,
    t,
  ]);

  if (unifiedGamemodeName(currentMap.game_mode) === "skirmish") {
    throw new Error("skirmish");
  }

  if (!sectorLayout.read) {
    return (
      <>
        <PageHeader
          eyebrow={t("navigation.groups.maps")}
          title={t("maps.objectives")}
          subtitle={t("maps.objectivesIntro")}
        />
        <PageState
          kind="offline"
          title={t("maps.objectivesUnavailableTitle")}
          description={t("maps.objectivesUnavailable")}
        />
      </>
    );
  }

  const playerCount =
    status?.current_players ??
    Number(gameState?.num_allied_players || 0) +
      Number(gameState?.num_axis_players || 0);

  return (
    <Box
      data-testid="objectives-workbench"
      sx={{
        width: "100%",
        maxWidth: 1540,
        minWidth: 0,
        mx: "auto",
        pb: 3,
        "& .MuiButton-root, & .MuiToggleButton-root, & .MuiOutlinedInput-root, & .MuiOutlinedInput-notchedOutline, & .MuiPaper-root":
          {
            borderRadius: 0,
          },
      }}
    >
      <PageHeader
        eyebrow={t("navigation.groups.maps")}
        title={t("maps.objectives")}
        subtitle={t("maps.objectivesIntro")}
      />

      {mobile && (
        <ToggleButtonGroup
          value={mobileView}
          exclusive
          fullWidth
          onChange={(_, next) => next && setMobileView(next)}
          aria-label={t("maps.mobileView")}
          sx={{
            mb: 1.25,
            "& .MuiToggleButton-root": { minWidth: 0, minHeight: 44 },
          }}
        >
          <ToggleButton value="map">
            <MapOutlinedIcon fontSize="small" sx={{ mr: 0.75 }} />
            {t("maps.objectivesWorkbench.mapTab")}
          </ToggleButton>
          <ToggleButton value="selection">
            <FormatListNumberedIcon fontSize="small" sx={{ mr: 0.75 }} />
            {t("maps.objectivesWorkbench.selectionTab")}
          </ToggleButton>
        </ToggleButtonGroup>
      )}

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "minmax(0, 1fr)",
            md: "minmax(0, 1.08fr) minmax(340px, 0.92fr)",
          },
          gap: 1.25,
          minWidth: 0,
        }}
      >
        {(!mobile || mobileView === "map") && (
          <Box
            component="section"
            sx={{ minWidth: 0, border: "1px solid", borderColor: "divider" }}
          >
            <SectionHeader
              eyebrow={t("maps.objectivesWorkbench.mapEyebrow")}
              title={currentMap.pretty_name}
              description={t("maps.objectivesWorkbench.mapDescription")}
              action={
                <Stack alignItems="flex-end" sx={{ flexShrink: 0 }}>
                  <Typography variant="overline" color="text.secondary">
                    {t("maps.objectivesWorkbench.selectedCount", {
                      count: selectedCount,
                    })}
                  </Typography>
                  <Typography variant="caption" color="primary.main">
                    {t("maps.objectivesWorkbench.randomCount", {
                      count: randomCount,
                    })}
                  </Typography>
                </Stack>
              }
            />
            <Divider />
            <Box sx={{ p: { xs: 1, sm: 1.5 } }}>
              <MapObjectivesPicker
                objectives={objectives}
                map={currentMap}
                onClick={handleObjectiveClick}
                loading={objectives === null || currentMap === null}
                disabled={!sectorLayout.set}
              />
            </Box>
          </Box>
        )}

        {(!mobile || mobileView === "selection") && (
          <Box
            component="section"
            sx={{ minWidth: 0, border: "1px solid", borderColor: "divider" }}
          >
            <SectionHeader
              eyebrow={t("maps.objectivesWorkbench.selectionEyebrow")}
              title={t("maps.objectivesWorkbench.selectionTitle")}
              description={t("maps.objectivesWorkbench.selectionDescription")}
            />
            <Divider />
            <Stack spacing={1.5} sx={{ p: { xs: 1.5, sm: 2 } }}>
              {(objectiveNames || []).map((names, index) => {
                const objectiveLabel = t("maps.objectiveNumber", {
                  number: index + 1,
                });
                const labelId = `objective-${index + 1}-label`;
                return (
                  <FormControl key={labelId} size="small" fullWidth>
                    <InputLabel id={labelId}>{objectiveLabel}</InputLabel>
                    <Select
                      id={`objective-${index + 1}`}
                      labelId={labelId}
                      value={selectedObjectives[index]}
                      disabled={!sectorLayout.set}
                      onChange={(event) =>
                        handleObjectiveNamePick(
                          index,
                          names.indexOf(event.target.value)
                        )
                      }
                      label={objectiveLabel}
                    >
                      <MenuItem value="random">{t("maps.random")}</MenuItem>
                      {names.map((name) => (
                        <MenuItem key={name} value={name}>
                          {name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                );
              })}

              <FormControl component="fieldset">
                <FormLabel component="legend">
                  {t("maps.randomCriteria")}
                </FormLabel>
                <FormGroup sx={{ mt: 0.5 }}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={randomConstraint["1"]}
                        disabled={!sectorLayout.set}
                        name="1"
                        onChange={handleConstraintChange}
                      />
                    }
                    label={t("maps.adjacent")}
                  />
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={randomConstraint["2"]}
                        disabled={!sectorLayout.set}
                        name="2"
                        onChange={handleConstraintChange}
                      />
                    }
                    label={t("maps.notStraight")}
                  />
                </FormGroup>
              </FormControl>

              <Box
                sx={{
                  border: "1px solid",
                  borderColor: "warning.dark",
                  bgcolor: "action.hover",
                }}
              >
                <Stack
                  direction="row"
                  spacing={1}
                  alignItems="center"
                  sx={{ px: 1.5, pt: 1.25 }}
                >
                  <RestartAltOutlinedIcon color="warning" />
                  <Typography variant="subtitle2" fontWeight={850}>
                    {t("maps.objectivesWorkbench.restartTitle")}
                  </Typography>
                </Stack>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ px: 1.5, py: 1 }}
                >
                  {t("maps.objectivesWorkbench.restartDescription", {
                    map: currentMap.pretty_name,
                  })}
                </Typography>
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                    borderTop: "1px solid",
                    borderColor: "divider",
                  }}
                >
                  <ImpactMetric
                    label={t("maps.objectivesWorkbench.affectedPlayers")}
                    value={
                      playerCount == null
                        ? t("common.unknown")
                        : String(playerCount)
                    }
                  />
                  <ImpactMetric
                    label={t("maps.objectivesWorkbench.currentServer")}
                    value={serverState?.name || t("common.unknown")}
                  />
                </Box>
              </Box>
            </Stack>
          </Box>
        )}
      </Box>

      <Stack
        direction={{ xs: "column-reverse", sm: "row" }}
        justifyContent="flex-end"
        gap={1}
        sx={{
          mt: 1.25,
          p: 1.25,
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.paper",
        }}
      >
        <Button
          variant="outlined"
          color="inherit"
          disabled={!sectorLayout.set || objectivesChanging}
          onClick={handleClearClick}
          startIcon={<DeleteOutlineIcon />}
        >
          {t("maps.objectivesWorkbench.clearPlan")}
        </Button>
        <Button
          variant="contained"
          color="warning"
          disabled={!sectorLayout.set || objectivesChanging}
          onClick={() => setConfirmDialogOpen(true)}
          startIcon={<RestartAltOutlinedIcon />}
        >
          {t("maps.objectivesWorkbench.applyPlan")}
        </Button>
      </Stack>

      <Dialog
        open={confirmDialogOpen}
        onClose={() => !objectivesChanging && setConfirmDialogOpen(false)}
        fullWidth
        maxWidth="sm"
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
      >
        <DialogTitle id="alert-dialog-title">
          {t("maps.objectivesWorkbench.restartTitle")}
        </DialogTitle>
        <DialogContent dividers>
          <DialogContentText id="alert-dialog-description">
            {t("maps.objectiveRestart")}
          </DialogContentText>
          <Box sx={{ mt: 2, border: "1px solid", borderColor: "divider" }}>
            <ImpactMetric
              label={t("maps.objectivesWorkbench.currentServer")}
              value={serverState?.name || t("common.unknown")}
            />
            <Divider />
            <ImpactMetric
              label={t("maps.current")}
              value={currentMap.pretty_name}
            />
            <Divider />
            <Stack spacing={0.5} sx={{ p: 1.5 }}>
              {selectedObjectives.map((objective, index) => (
                <Typography key={`${objective}-${index}`} variant="body2">
                  {t("maps.objectiveNumber", { number: index + 1 })} –{" "}
                  {objective === "random" ? t("maps.random") : objective}
                </Typography>
              ))}
            </Stack>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setConfirmDialogOpen(false)}
            color="inherit"
            disabled={objectivesChanging}
          >
            {t("common.cancel")}
          </Button>
          <Button
            onClick={handleDialogConfirmationClick}
            disabled={!sectorLayout.set || objectivesChanging}
            color="warning"
            variant="contained"
            startIcon={<CheckCircleIcon />}
          >
            {t("maps.objectivesWorkbench.applyPlan")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default MapObjectivesPage;
