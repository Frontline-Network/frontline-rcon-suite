import { Box, Button, Stack, Typography } from "@mui/material";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import MapOutlinedIcon from "@mui/icons-material/MapOutlined";
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  TouchSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { useTranslation } from "react-i18next";
import CopyToClipboardButton from "@/components/shared/CopyToClipboardButton";
import SortableRotationItem from "./SortableRotationItem";

export function SortableRotationList({
  maps,
  setMaps,
  onRemove,
  onClear,
  actions,
  params,
  emptyTitle,
  emptyDescription,
  removeTooltip,
  showNext = true,
}) {
  const { t } = useTranslation();
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 10 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
    useSensor(TouchSensor)
  );

  const moveItem = (from, to) => {
    if (to < 0 || to >= maps.length || from === to) return;
    setMaps((items) => arrayMove(items, from, to));
  };

  const handleDragEnd = ({ active, over }) => {
    if (!over || active.id === over.id) return;
    const oldIndex = maps.findIndex((item) => item.selectionId === active.id);
    const newIndex = maps.findIndex((item) => item.selectionId === over.id);
    moveItem(oldIndex, newIndex);
  };

  return (
    <Box>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        justifyContent="space-between"
        alignItems={{ xs: "stretch", sm: "center" }}
        gap={1}
        sx={{
          px: 1.5,
          py: 1,
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Typography variant="caption" color="text.secondary">
          {t("maps.rotationWorkbench.orderHint")}
        </Typography>
        <Stack direction="row" spacing={0.75} justifyContent="flex-end">
          {actions}
          <CopyToClipboardButton
            title={t("maps.copySelectedMapIds")}
            text={JSON.stringify(
              maps.map((item) => item.mapId || item.id),
              null,
              2
            )}
            size="small"
          />
          <Button
            variant="text"
            color="error"
            size="small"
            startIcon={<DeleteOutlineIcon />}
            disabled={!maps.length}
            onClick={onClear}
          >
            {t("common.clearSelection")}
          </Button>
        </Stack>
      </Stack>

      <Box
        sx={{
          minHeight: 260,
          maxHeight: { xs: "none", md: 580 },
          overflowY: { xs: "visible", md: "auto" },
          scrollbarWidth: "thin",
        }}
      >
        {maps.length > 0 ? (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext
              items={maps.map((item) => item.selectionId)}
              strategy={verticalListSortingStrategy}
            >
              {maps.map((item, index) => {
                let isNext = false;
                if (showNext && maps.length === 1) {
                  isNext = true;
                } else if (
                  showNext &&
                  params.currentMapIndex === params.nextMapIndex
                ) {
                  isNext = index + 1 === params.nextMapIndex;
                } else if (showNext) {
                  isNext = index === params.nextMapIndex;
                }

                return (
                  <SortableRotationItem
                    key={item.selectionId}
                    item={item}
                    index={index}
                    total={maps.length}
                    onMove={moveItem}
                    onRemove={onRemove}
                    isNext={isNext}
                    removeTooltip={removeTooltip}
                  />
                );
              })}
            </SortableContext>
          </DndContext>
        ) : (
          <Stack
            alignItems="center"
            justifyContent="center"
            spacing={1}
            sx={{ minHeight: 300, px: 2, textAlign: "center" }}
          >
            <MapOutlinedIcon sx={{ fontSize: 44, color: "text.disabled" }} />
            <Typography variant="h6">
              {emptyTitle || t("maps.noMapsInRotation")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {emptyDescription || t("maps.addMapsToRotation")}
            </Typography>
          </Stack>
        )}
      </Box>
    </Box>
  );
}
