import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import {
  alpha,
  Box,
  CircularProgress,
  styled,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import { getTacMapImageSrc } from "./helpers";

const InteractiveContainer = styled("div")(({ theme }) => ({
  position: "relative",
  width: "100%",
  aspectRatio: "1 / 1",
  overflow: "hidden",
  border: `1px solid ${theme.palette.divider}`,
  background: theme.palette.background.default,
}));

const MapImg = styled("img")({
  position: "absolute",
  inset: 0,
  width: "100%",
  height: "100%",
  objectFit: "cover",
  touchAction: "none",
  userSelect: "none",
});

const ObjectivesGrid = styled("div")({
  position: "absolute",
  inset: 0,
  display: "grid",
  gridTemplateColumns: "repeat(5, minmax(0, 1fr))",
  gridTemplateRows: "repeat(5, minmax(0, 1fr))",
});

const ControlButton = styled("button", {
  shouldForwardProp: (prop) => prop !== "cellState",
})(({ theme, cellState }) => ({
  position: "relative",
  display: "grid",
  placeItems: "center",
  minWidth: 0,
  minHeight: 0,
  padding: 0,
  border: `1px solid ${alpha(theme.palette.common.white, 0.24)}`,
  borderRadius: 0,
  color: theme.palette.common.white,
  background: alpha(theme.palette.common.black, 0.12),
  cursor: "pointer",
  transition: theme.transitions.create(["background-color", "border-color"]),
  "&:hover:not(:disabled)": {
    borderColor: theme.palette.primary.light,
    background: alpha(theme.palette.primary.main, 0.18),
  },
  "&:focus-visible": {
    zIndex: 2,
    outline: `3px solid ${theme.palette.info.main}`,
    outlineOffset: -3,
  },
  "&:disabled": { cursor: "not-allowed" },
  ...(cellState === true && {
    zIndex: 1,
    border: `2px solid ${theme.palette.primary.light}`,
    background: alpha(theme.palette.primary.main, 0.38),
  }),
  ...(cellState === false && {
    "&:disabled": {
      background: alpha(theme.palette.common.black, 0.42),
      color: alpha(theme.palette.common.white, 0.54),
    },
  }),
  ...(cellState === null && {
    borderColor: alpha(theme.palette.common.black, 0.55),
    background: alpha(theme.palette.common.black, 0.72),
    color: theme.palette.text.disabled,
  }),
}));

const isButtonDisabled = (state, index, map, objectives) => {
  if (state === null) return true;
  if (state === true) return false;

  const targetIndex = index % 5;
  const targetRow = Math.floor(index / 5);

  if (map.map.orientation === "vertical") {
    return objectives[targetRow].includes(true);
  }

  return objectives.some((row) => row[targetIndex] === true);
};

export function MapObjectivesPicker({
  objectives,
  map,
  onClick,
  loading,
  disabled = false,
}) {
  const { t } = useTranslation();

  return (
    <InteractiveContainer data-testid="objective-tactical-map">
      <MapImg
        src={getTacMapImageSrc(map)}
        alt={map.pretty_name}
        draggable={false}
      />
      <ObjectivesGrid>
        {loading ? (
          <Box
            sx={{
              gridArea: "1 / 1 / 6 / 6",
              display: "grid",
              placeItems: "center",
              bgcolor: (theme) => alpha(theme.palette.common.black, 0.72),
            }}
          >
            <CircularProgress aria-label={t("common.loading")} />
          </Box>
        ) : (
          objectives.flat().map((state, index) => {
            const row = Math.floor(index / 5) + 1;
            const column = (index % 5) + 1;
            const objectiveNumber =
              map.map.orientation === "vertical" ? row : column;
            const stateLabel =
              state === true
                ? t("maps.objectiveSelected")
                : state === false
                ? t("maps.objectiveAvailable")
                : t("maps.objectiveUnavailable");

            return (
              <ControlButton
                key={index}
                type="button"
                onClick={() => onClick(index)}
                disabled={
                  disabled || isButtonDisabled(state, index, map, objectives)
                }
                cellState={state}
                aria-label={t("maps.objectiveGridCell", {
                  row,
                  column,
                  state: stateLabel,
                })}
                aria-pressed={state === null ? undefined : state}
              >
                {state === true && (
                  <Box
                    aria-hidden="true"
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      gap: 0.5,
                      px: 0.75,
                      py: 0.35,
                      bgcolor: "background.paper",
                      border: "1px solid",
                      borderColor: "primary.main",
                    }}
                  >
                    <CheckCircleOutlineIcon sx={{ fontSize: 16 }} />
                    <Typography
                      component="span"
                      variant="caption"
                      fontWeight={850}
                    >
                      {objectiveNumber}
                    </Typography>
                  </Box>
                )}
              </ControlButton>
            );
          })
        )}
      </ObjectivesGrid>
    </InteractiveContainer>
  );
}
