import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Stack,
  TextField,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import BookmarkAddOutlinedIcon from "@mui/icons-material/BookmarkAddOutlined";
import BookmarkBorderOutlinedIcon from "@mui/icons-material/BookmarkBorderOutlined";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import { getMapEnvironmentLabel, getMapModeLabel } from "@/utils/mapLabels";

const viewSummary = (t, filters) => {
  const parts = [];
  if (filters.search) {
    parts.push(t("stats.games.savedViewSearch", { value: filters.search }));
  }
  if (filters.period !== "all") {
    parts.push(t("stats.games.lastDays", { count: Number(filters.period) }));
  }
  if (filters.environment !== "all") {
    parts.push(getMapEnvironmentLabel(t, filters.environment));
  }
  if (filters.mode !== "all") {
    parts.push(getMapModeLabel(t, filters.mode));
  }
  return parts.length ? parts.join(" · ") : t("stats.games.savedViewAllGames");
};

export function SavedGameViewsDialog({
  activeViewId,
  currentFilters,
  onApply,
  onClose,
  onDelete,
  onSave,
  open,
  savedViews,
}) {
  const { t } = useTranslation();
  const theme = useTheme();
  const compact = useMediaQuery(theme.breakpoints.down("sm"));
  const [name, setName] = useState("");
  const currentSummary = useMemo(
    () => viewSummary(t, currentFilters),
    [currentFilters, t]
  );

  useEffect(() => {
    if (open) setName("");
  }, [open]);

  const save = () => {
    const normalizedName = name.trim();
    if (!normalizedName) return;
    onSave(normalizedName);
    setName("");
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      fullScreen={compact}
      fullWidth
      maxWidth="sm"
      aria-labelledby="saved-game-views-title"
      PaperProps={{
        sx: {
          border: "1px solid",
          borderColor: "divider",
          backgroundImage: "none",
        },
      }}
    >
      <DialogTitle
        id="saved-game-views-title"
        sx={{ borderBottom: "1px solid", borderColor: "divider" }}
      >
        {t("stats.games.savedViewsTitle")}
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          {t("stats.games.savedViewsSubtitle")}
        </Typography>
      </DialogTitle>

      <DialogContent sx={{ p: { xs: 2, sm: 2.5 } }}>
        <Stack spacing={2.5}>
          <Box
            component="section"
            aria-labelledby="save-current-game-view"
            sx={{ border: "1px solid", borderColor: "divider", p: 1.5 }}
          >
            <Typography id="save-current-game-view" variant="overline">
              {t("stats.games.saveCurrentView")}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
              {currentSummary}
            </Typography>
            <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
              <TextField
                autoFocus
                fullWidth
                size="small"
                label={t("stats.games.savedViewName")}
                value={name}
                inputProps={{ maxLength: 40 }}
                onChange={(event) => setName(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key !== "Enter") return;
                  event.preventDefault();
                  save();
                }}
              />
              <Button
                variant="contained"
                startIcon={<BookmarkAddOutlinedIcon />}
                disabled={!name.trim()}
                onClick={save}
                sx={{ minHeight: 40, whiteSpace: "nowrap" }}
              >
                {t("common.save")}
              </Button>
            </Stack>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
              {t("stats.games.savedViewsLocalHint")}
            </Typography>
          </Box>

          <Box component="section" aria-labelledby="saved-game-view-list">
            <Typography id="saved-game-view-list" variant="overline">
              {t("stats.games.savedViewsList")}
            </Typography>
            {savedViews.length ? (
              <Stack
                sx={{ mt: 1, border: "1px solid", borderColor: "divider" }}
              >
                {savedViews.map((view) => {
                  const active = view.id === activeViewId;
                  return (
                    <Box
                      key={view.id}
                      sx={{
                        display: "grid",
                        gridTemplateColumns: "minmax(0, 1fr) auto auto",
                        gap: 0.75,
                        alignItems: "center",
                        minHeight: 58,
                        px: 1.25,
                        py: 0.75,
                        borderBottom: "1px solid",
                        borderColor: "divider",
                        bgcolor: active ? "action.selected" : "transparent",
                        "&:last-of-type": { borderBottom: 0 },
                      }}
                    >
                      <Box sx={{ minWidth: 0 }}>
                        <Typography
                          sx={{ fontWeight: active ? 700 : 500 }}
                          noWrap
                        >
                          {view.name}
                        </Typography>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          noWrap
                        >
                          {viewSummary(t, view.filters)}
                        </Typography>
                      </Box>
                      <Button
                        size="small"
                        startIcon={<BookmarkBorderOutlinedIcon />}
                        aria-pressed={active}
                        onClick={() => onApply(view.filters)}
                      >
                        {active
                          ? t("stats.games.savedViewActive")
                          : t("stats.games.applySavedView")}
                      </Button>
                      <IconButton
                        size="small"
                        color="error"
                        aria-label={t("stats.games.deleteSavedView", {
                          name: view.name,
                        })}
                        onClick={() => onDelete(view.id)}
                      >
                        <DeleteOutlineIcon fontSize="small" />
                      </IconButton>
                    </Box>
                  );
                })}
              </Stack>
            ) : (
              <Box
                sx={{
                  mt: 1,
                  border: "1px dashed",
                  borderColor: "divider",
                  p: 2,
                }}
              >
                <Typography variant="body2" color="text.secondary">
                  {t("stats.games.noSavedViews")}
                </Typography>
              </Box>
            )}
          </Box>
        </Stack>
      </DialogContent>

      <DialogActions
        sx={{ borderTop: "1px solid", borderColor: "divider", p: 1.5 }}
      >
        <Button onClick={onClose}>{t("common.close")}</Button>
      </DialogActions>
    </Dialog>
  );
}
