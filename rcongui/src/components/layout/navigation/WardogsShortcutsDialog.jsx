import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Stack,
  TextField,
  Tooltip,
  Typography,
  useMediaQuery,
} from "@mui/material";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";
import CloseIcon from "@mui/icons-material/Close";
import CheckBoxOutlinedIcon from "@mui/icons-material/CheckBoxOutlined";
import CheckBoxOutlineBlankOutlinedIcon from "@mui/icons-material/CheckBoxOutlineBlankOutlined";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "react-toastify";
import { useAuth } from "@/hooks/useAuth";
import { useAppStore } from "@/stores/app-state";
import { cmd } from "@/utils/fetchUtils";
import {
  DEFAULT_WARDOGS_SHORTCUTS,
  MAX_WARDOGS_SHORTCUTS,
  moveWardogsShortcut,
  normalizeWardogsShortcuts,
  resolveWardogsShortcuts,
} from "./wardogs-shortcuts.mjs";

export default function WardogsShortcutsDialog({ links, onClose }) {
  const { t } = useTranslation();
  const { permissions } = useAuth();
  const queryClient = useQueryClient();
  const compact = useMediaQuery((theme) => theme.breakpoints.down("sm"));
  const appearance = useAppStore((state) => state.appearance);
  const setAppearance = useAppStore((state) => state.setAppearance);
  const [draft, setDraft] = useState(() =>
    normalizeWardogsShortcuts(appearance.wardogsShortcuts)
  );
  const [search, setSearch] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(false);
  const [announcement, setAnnouncement] = useState("");
  const dirty =
    JSON.stringify(draft) !== JSON.stringify(appearance.wardogsShortcuts);
  const selected = resolveWardogsShortcuts(draft, links);
  const selectedRoutes = selected.map((link) => link.to);
  const filtered = links.filter((link) =>
    `${link.label} ${link.groupLabel}`
      .toLocaleLowerCase()
      .includes(search.trim().toLocaleLowerCase())
  );
  const toggle = (link) => {
    setDraft((current) =>
      current.includes(link.to)
        ? current.filter((route) => route !== link.to)
        : [...current, link.to]
    );
    setAnnouncement(
      t(
        draft.includes(link.to)
          ? "navigation.shortcuts.removed"
          : "navigation.shortcuts.added",
        { name: link.label }
      )
    );
  };
  const move = (link, offset) => {
    // Reorder visible destinations without losing saved, temporarily locked ones.
    const visible = moveWardogsShortcut(selectedRoutes, link.to, offset);
    let index = 0;
    setDraft((current) =>
      current.map((route) =>
        selectedRoutes.includes(route) ? visible[index++] : route
      )
    );
    setAnnouncement(
      t("navigation.shortcuts.moved", {
        name: link.label,
        position: visible.indexOf(link.to) + 1,
      })
    );
  };
  const save = async () => {
    setSaving(true);
    setError(false);
    try {
      const next = {
        ...useAppStore.getState().appearance,
        wardogsShortcuts: draft,
      };
      const response = await cmd.SET_OWN_APPEARANCE(next);
      if (!Array.isArray(response?.result?.wardogsShortcuts))
        throw new Error("Shortcut preference was not saved");
      setAppearance(response.result);
      queryClient.setQueryData(
        ["user", "appearance", permissions?.user_name],
        response.result
      );
      toast.success(t("navigation.shortcuts.saved"));
      onClose();
    } catch {
      setError(true);
    } finally {
      setSaving(false);
    }
  };
  const panelSx = {
    border: "1px solid",
    borderColor: "divider",
    borderRadius: "12px",
    bgcolor: "background.default",
    overflowY: "auto",
    maxHeight: { xs: 240, sm: 340 },
  };

  return (
    <Dialog
      open
      onClose={saving ? undefined : onClose}
      fullWidth
      maxWidth="md"
      fullScreen={compact}
      aria-labelledby="wardogs-shortcuts-title"
    >
      <DialogTitle
        id="wardogs-shortcuts-title"
        sx={{ display: "flex", alignItems: "center", gap: 1 }}
      >
        <Box sx={{ flex: 1 }}>{t("navigation.shortcuts.title")}</Box>
        <IconButton
          onClick={onClose}
          disabled={saving}
          aria-label={t("common.close")}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent dividers>
        <Typography color="text.secondary" sx={{ mb: 2 }}>
          {t("navigation.shortcuts.description")}
        </Typography>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {t("navigation.shortcuts.saveFailed")}
          </Alert>
        )}
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
            gap: 2.5,
          }}
        >
          <Box
            component="section"
            aria-labelledby="shortcuts-selected-title"
            sx={{ minWidth: 0 }}
          >
            <Typography
              id="shortcuts-selected-title"
              component="h3"
              variant="subtitle1"
              sx={{ mb: 1 }}
            >
              {t("navigation.shortcuts.selected", { count: selected.length })}
            </Typography>
            <Box sx={panelSx}>
              {selected.length === 0 && (
                <Typography color="text.secondary" sx={{ p: 2 }}>
                  {t("navigation.shortcuts.empty")}
                </Typography>
              )}
              <List
                component="ol"
                disablePadding
                aria-label={t("navigation.shortcuts.order")}
              >
                {selected.map((link, index) => (
                  <Stack
                    component="li"
                    key={link.to}
                    direction="row"
                    alignItems="center"
                    sx={{
                      pl: 1.5,
                      pr: 0.5,
                      minHeight: 64,
                      gap: 1,
                      borderBottom:
                        index < selected.length - 1 ? "1px solid" : 0,
                      borderColor: "divider",
                    }}
                  >
                    <Box sx={{ color: "primary.main", display: "flex" }}>
                      {link.icon}
                    </Box>
                    <Typography
                      variant="body2"
                      sx={{ flex: 1, minWidth: 0, overflowWrap: "anywhere" }}
                    >
                      {link.label}
                    </Typography>
                    <Stack direction="row" spacing={0}>
                      {[
                        [-1, ArrowUpwardIcon, "up"],
                        [1, ArrowDownwardIcon, "down"],
                      ].map(([offset, Icon, direction]) => (
                        <Tooltip
                          title={t(`navigation.shortcuts.${direction}`, {
                            name: link.label,
                          })}
                          key={direction}
                        >
                          <span>
                            <IconButton
                              disabled={
                                saving ||
                                index + offset < 0 ||
                                index + offset >= selected.length
                              }
                              onClick={() => move(link, offset)}
                              aria-label={t(
                                `navigation.shortcuts.${direction}`,
                                { name: link.label }
                              )}
                              sx={{ width: 36, height: 44 }}
                            >
                              <Icon fontSize="small" />
                            </IconButton>
                          </span>
                        </Tooltip>
                      ))}
                      <IconButton
                        disabled={saving}
                        onClick={() => toggle(link)}
                        aria-label={t("navigation.shortcuts.remove", {
                          name: link.label,
                        })}
                        sx={{ width: 36, height: 44 }}
                      >
                        <CloseIcon fontSize="small" />
                      </IconButton>
                    </Stack>
                  </Stack>
                ))}
              </List>
            </Box>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ display: "block", mt: 1 }}
            >
              {t("navigation.shortcuts.fixed")}
            </Typography>
          </Box>
          <Box
            component="section"
            aria-labelledby="shortcuts-available-title"
            sx={{ minWidth: 0 }}
          >
            <Typography
              id="shortcuts-available-title"
              component="h3"
              variant="subtitle1"
              sx={{ mb: 1 }}
            >
              {t("navigation.shortcuts.available")}
            </Typography>
            <TextField
              fullWidth
              size="small"
              label={t("navigation.search")}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              sx={{ mb: 1 }}
            />
            <List
              component="div"
              role="group"
              aria-label={t("navigation.shortcuts.available")}
              disablePadding
              sx={panelSx}
            >
              {filtered.map((link) => (
                <ListItemButton
                  key={link.to}
                  role="checkbox"
                  aria-checked={draft.includes(link.to)}
                  aria-label={link.label}
                  selected={draft.includes(link.to)}
                  disabled={
                    saving ||
                    (!draft.includes(link.to) &&
                      draft.length >= MAX_WARDOGS_SHORTCUTS)
                  }
                  onClick={() => toggle(link)}
                  sx={{ minHeight: 64 }}
                >
                  <ListItemIcon
                    sx={{
                      minWidth: 34,
                      color: draft.includes(link.to)
                        ? "primary.main"
                        : "text.secondary",
                    }}
                  >
                    {draft.includes(link.to) ? (
                      <CheckBoxOutlinedIcon />
                    ) : (
                      <CheckBoxOutlineBlankOutlinedIcon />
                    )}
                  </ListItemIcon>
                  <ListItemText
                    primary={link.label}
                    secondary={link.groupLabel}
                  />
                  <Box sx={{ color: "text.secondary", display: "flex", ml: 1 }}>
                    {link.icon}
                  </Box>
                </ListItemButton>
              ))}
              {filtered.length === 0 && (
                <Typography color="text.secondary" sx={{ p: 2 }}>
                  {t("navigation.noResults")}
                </Typography>
              )}
            </List>
          </Box>
        </Box>
        <Box
          role="status"
          aria-live="polite"
          sx={{
            position: "absolute",
            width: "1px",
            height: "1px",
            top: 0,
            left: 0,
            overflow: "hidden",
            clipPath: "inset(50%)",
          }}
        >
          {announcement}
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 2, py: 1.5, flexWrap: "wrap", gap: 1 }}>
        <Button
          disabled={saving}
          onClick={() => setDraft([...DEFAULT_WARDOGS_SHORTCUTS])}
          sx={{ mr: "auto" }}
        >
          {t("navigation.shortcuts.reset")}
        </Button>
        <Button disabled={saving} onClick={onClose} color="inherit">
          {t("common.cancel")}
        </Button>
        <Button variant="contained" disabled={!dirty || saving} onClick={save}>
          {t("common.save")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
