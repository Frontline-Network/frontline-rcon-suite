import {
  Box,
  Divider,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import { MapListItem, MapVotemapWhitelistItem } from "./MapListItem";
import CopyToClipboardButton from "@/components/shared/CopyToClipboardButton";
import SaveIcon from "@mui/icons-material/Save";
import DeleteIcon from "@mui/icons-material/Delete";
import ReplayIcon from "@mui/icons-material/Replay";
import MapIcon from "@mui/icons-material/Map";
import { useTranslation } from "react-i18next";

const EmptyMapList = ({ reason }) => {
  const { t } = useTranslation();
  return (
    <Box
      sx={{
        py: 5,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        color: "text.secondary",
      }}
    >
      <Box sx={{ mb: 2, opacity: 0.5 }}>
        <MapIcon sx={{ fontSize: 48 }} />
      </Box>
      <Typography variant="h6" gutterBottom>
        {t("maps.noMaps")}
      </Typography>
      <Typography variant="body2">
        {reason ?? t("maps.adjustFilters")}
      </Typography>
    </Box>
  );
};

/**
 * The maps are sorted alphabetically be default
 * @param {React.ReactNode} renderItem (optional) custom item component that accepts `mapLayer` as the only param
 * @returns
 */
export const MapList = ({
  maps,
  renderItem,
  sort = true,
  emptyListMessage,
  ...props
}) => {
  if (maps.length === 0) {
    return <EmptyMapList reason={emptyListMessage} />;
  }

  return (
    <Box sx={{ overflow: "auto" }} {...props}>
      {(sort
        ? [...maps].sort((a, b) => a.map.name.localeCompare(b.map.name))
        : maps
      ).map((mapLayer, index, arr) =>
        renderItem ? (
          renderItem(mapLayer, index, arr)
        ) : (
          <MapListItem
            key={mapLayer.selectionId || mapLayer.id}
            mapLayer={mapLayer}
          />
        )
      )}
    </Box>
  );
};

export const MapWhitelistList = ({
  maps,
  onReset,
  onRemove,
  onSave,
  onClear,
  isSaving,
  isDisabled,
  actions,
}) => {
  const { t } = useTranslation();
  return (
    <Box
      sx={{
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 1,
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Box sx={{ p: 2, borderBottom: "1px solid", borderColor: "divider" }}>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          gap={1}
          alignItems={{ sx: "flex-start", md: "center" }}
          justifyContent={"space-between"}
        >
          <Typography variant="h6">{t("maps.whitelist")} ({maps.length})</Typography>
          <Stack
            direction="row"
            spacing={1}
            justifyContent={{ sx: "center", md: "flex-end" }}
          >
            {actions && (
              <>
                <Box
                  sx={{
                    flexGrow: 1,
                    display: "flex",
                    justifyContent: "flex-end",
                    gap: 1,
                  }}
                >
                  {actions}
                </Box>
                <Divider flexItem orientation="vertical" />
              </>
            )}
            <Box
              sx={{
                display: "flex",
                justifyContent: "flex-end",
                gap: 1,
              }}
            >
              <Tooltip title={t("maps.resetChanges")}>
                <IconButton
                  variant="outlined"
                  size={"small"}
                  color="error"
                  onClick={onReset}
                >
                  <ReplayIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title={t("common.clearSelection")}>
                <IconButton
                  variant="outlined"
                  size={"small"}
                  color="error"
                  onClick={onClear}
                >
                  <DeleteIcon />
                </IconButton>
              </Tooltip>
              <CopyToClipboardButton
                iconOnly={true}
                title={
                  <div>
                    <div>
                      {t("maps.copySelectedMapIds")}
                    </div>
                    <div>{t("maps.copyMapIdsHint")}</div>
                  </div>
                }
                text={JSON.stringify(
                  maps.map((item) => item.mapId || item.id),
                  null,
                  2
                )}
                size={"small"}
              />
              <Tooltip title={t("common.save")}>
                <IconButton
                  variant="contained"
                  size={"small"}
                  color="primary"
                  disabled={isDisabled}
                  onClick={onSave}
                >
                  <SaveIcon />
                </IconButton>
              </Tooltip>
            </Box>
          </Stack>
        </Stack>
      </Box>
      <MapList
        maps={maps}
        renderItem={(mapLayer) => (
          <MapVotemapWhitelistItem
            key={mapLayer.selectionId || mapLayer.id}
            mapLayer={mapLayer}
            onClick={onRemove}
          />
        )}
        sx={{ p: 2 }}
      />
    </Box>
  );
};
