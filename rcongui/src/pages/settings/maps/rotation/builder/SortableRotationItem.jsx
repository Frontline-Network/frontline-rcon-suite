import {
  Box,
  Chip,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import CloseIcon from "@mui/icons-material/Close";
import DragIndicatorIcon from "@mui/icons-material/DragIndicator";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useTranslation } from "react-i18next";
import { getMapEnvironmentLabel, getMapModeLabel } from "@/utils/mapLabels";
import {
  getMapLayerImageSrc,
  unifiedGamemodeName,
} from "../../objectives/helpers";

function SortableRotationItem({
  item,
  index,
  total,
  onMove,
  onRemove,
  isNext,
  removeTooltip,
}) {
  const { t } = useTranslation();
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: item.selectionId });
  const mode = unifiedGamemodeName(item.game_mode);
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 10 : 1,
    opacity: isDragging ? 0.75 : 1,
  };

  return (
    <Box
      ref={setNodeRef}
      style={style}
      component="article"
      sx={{
        display: "grid",
        gridTemplateColumns: {
          xs: "34px 66px minmax(0, 1fr) auto",
          sm: "42px 78px minmax(0, 1fr) auto",
        },
        minHeight: 72,
        alignItems: "stretch",
        borderBottom: "1px solid",
        borderColor: "divider",
        bgcolor: isNext ? "action.selected" : "transparent",
        boxShadow: isDragging ? 6 : 0,
        "&:hover": { bgcolor: "action.hover" },
      }}
    >
      <Tooltip title={t("maps.rotationWorkbench.dragHint")}>
        <IconButton
          {...attributes}
          {...listeners}
          aria-label={t("maps.rotationWorkbench.moveMap", {
            map: item.map.pretty_name,
          })}
          sx={{
            borderRight: "1px solid",
            borderColor: "divider",
            cursor: isDragging ? "grabbing" : "grab",
            touchAction: "none",
          }}
        >
          <DragIndicatorIcon fontSize="small" />
        </IconButton>
      </Tooltip>

      <Box
        component="img"
        src={getMapLayerImageSrc(item)}
        alt=""
        sx={{ width: "100%", height: "100%", minHeight: 72, objectFit: "cover" }}
      />

      <Stack justifyContent="center" sx={{ px: 1.5, minWidth: 0 }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ minWidth: 0 }}>
          <Typography variant="overline" color="text.secondary">
            {String(index + 1).padStart(2, "0")}
          </Typography>
          <Typography variant="body2" fontWeight={850} noWrap>
            {item.map.pretty_name}
          </Typography>
          {isNext && (
            <Chip
              size="small"
              color="secondary"
              label={t("maps.next")}
              sx={{ height: 22 }}
            />
          )}
        </Stack>
        <Typography variant="caption" color="text.secondary" noWrap>
          {getMapModeLabel(t, mode)}
          {mode === "offensive" && item.attackers ? ` (${item.attackers})` : ""} ·{" "}
          {getMapEnvironmentLabel(t, item.environment)}
        </Typography>
      </Stack>

      <Stack
        direction="row"
        alignItems="center"
        sx={{ px: 0.5, borderLeft: "1px solid", borderColor: "divider" }}
      >
        <Tooltip title={t("maps.rotationWorkbench.moveUp")}>
          <span>
            <IconButton
              size="small"
              disabled={index === 0}
              onClick={() => onMove(index, index - 1)}
              aria-label={t("maps.rotationWorkbench.moveUpNamed", {
                map: item.map.pretty_name,
              })}
            >
              <ArrowUpwardIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
        <Tooltip title={t("maps.rotationWorkbench.moveDown")}>
          <span>
            <IconButton
              size="small"
              disabled={index === total - 1}
              onClick={() => onMove(index, index + 1)}
              aria-label={t("maps.rotationWorkbench.moveDownNamed", {
                map: item.map.pretty_name,
              })}
            >
              <ArrowDownwardIcon fontSize="small" />
            </IconButton>
          </span>
        </Tooltip>
        <Tooltip title={removeTooltip || t("maps.removeFromRotation")}>
          <IconButton
            size="small"
            onClick={() => onRemove(item)}
            color="error"
            aria-label={removeTooltip || t("maps.removeFromRotation")}
          >
            <CloseIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Stack>
    </Box>
  );
}

export default SortableRotationItem;
