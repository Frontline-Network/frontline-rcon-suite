import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { selectAppLanguage } from "@/i18n";
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  IconButton,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import GridViewOutlinedIcon from "@mui/icons-material/GridViewOutlined";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";
import PaletteOutlinedIcon from "@mui/icons-material/PaletteOutlined";
import DashboardOutlinedIcon from "@mui/icons-material/DashboardOutlined";
import { useAppStore } from "@/stores/app-state";
import { alpha, lighten } from "@mui/material/styles";

const illustrations = { "theme-collection": "/updates/theme-collection.png" };
const icons = {
  shortcuts: GridViewOutlinedIcon,
  book: MenuBookOutlinedIcon,
  palette: PaletteOutlinedIcon,
  overview: DashboardOutlinedIcon,
};

export default function ReleaseHighlightsDialog({
  release,
  preview,
  onClose,
  onLater,
}) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const setAppearanceOpen = useAppStore(
    (state) => state.setAppearanceDialogOpen
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(false);
  const selectedLanguage = (i18n.resolvedLanguage || "en").split("-")[0];
  const lang = ["de", "en", "fr"].includes(selectedLanguage) ? selectedLanguage : "en";
  // Older release data may have only DE/EN; future highlights can include FR.
  const localized = (values) => values?.[lang] || values?.en || values?.de || "";
  const content = release.highlights;
  const changeLanguage = async (_, language) => {
    if (!language) return;
    await selectAppLanguage(language);
  };
  const openAction = () => {
    onClose();
    if (content.action?.id === "appearance") setAppearanceOpen(true);
    if (content.action?.id === "documentation") navigate("/documentation");
    if (content.action?.id === "overview") navigate("/");
  };
  const postpone = async () => {
    setSaving(true);
    setError(false);
    try {
      await onLater();
    } catch {
      setError(true);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog
      open
      onClose={saving ? undefined : onClose}
      aria-labelledby="release-spotlight-title"
      aria-describedby="release-spotlight-description"
      maxWidth={false}
      slotProps={{
        backdrop: {
          sx: {
            backgroundColor: "rgba(0, 0, 0, 0.56)",
            backdropFilter: "blur(2px)",
          },
        },
      }}
      PaperProps={{
        sx: (theme) => ({
          width: 760,
          maxWidth: "calc(100% - 32px)",
          maxHeight: "calc(100dvh - 32px)",
          m: 2,
          borderRadius: "14px",
          backgroundImage: `radial-gradient(ellipse 76% 58% at 44% 44%, ${alpha(
            theme.palette.primary.main,
            theme.palette.mode === "dark" ? 0.34 : 0.16
          )} 0%, ${alpha(
            theme.palette.primary.main,
            0.08
          )} 48%, transparent 78%)`,
          bgcolor:
            theme.palette.mode === "dark" ? "#151517" : "background.paper",
          overflow: "hidden",
          border: "1px solid",
          borderColor: alpha(theme.palette.text.primary, 0.17),
          boxShadow: `0 30px 110px ${alpha("#000", 0.6)}`,
        }),
      }}
    >
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        gap={1}
        sx={{ px: { xs: 2.5, sm: 4 }, pt: 2.5, pb: 1, flexShrink: 0 }}
      >
        <Typography
          variant="overline"
          color="primary.main"
          sx={{
            fontWeight: 700,
            letterSpacing: ".1em",
            lineHeight: 1.4,
            fontSize: ".76rem",
            textTransform: "uppercase",
          }}
        >
          {t(
            preview ? "releaseHighlights.preview" : "releaseHighlights.eyebrow"
          )}{" "}
          · {release.tag_name}
        </Typography>
        <Stack direction="row" alignItems="center" gap={1}>
          <ToggleButtonGroup
            exclusive
            value={lang}
            onChange={changeLanguage}
            size="small"
            aria-label={t("releaseHighlights.language")}
            sx={{
              "& .MuiToggleButton-root": {
                border: 0,
                px: 1,
                py: 0.5,
                minWidth: 36,
                fontSize: ".7rem",
              },
            }}
          >
            <ToggleButton value="de" aria-label="Deutsch" lang="de">
              DE
            </ToggleButton>
            <ToggleButton value="en" aria-label="English" lang="en">
              EN
            </ToggleButton>
            <ToggleButton value="fr" aria-label="Français" lang="fr">
              FR
            </ToggleButton>
          </ToggleButtonGroup>
          <IconButton
            onClick={onClose}
            disabled={saving}
            aria-label={t("releaseHighlights.close")}
            size="small"
          >
            <CloseIcon fontSize="small" />
          </IconButton>
        </Stack>
      </Stack>
      <DialogContent
        sx={{ px: { xs: 2.5, sm: 4 }, pt: 1.5, pb: 0, overflowX: "hidden" }}
      >
        <Typography
          id="release-spotlight-title"
          component="h2"
          sx={{
            fontSize: { xs: "1.85rem", sm: "2.65rem" },
            fontWeight: 750,
            lineHeight: 1.2,
            letterSpacing: "-.035em",
            mb: 1.5,
            color: (theme) =>
              theme.palette.mode === "dark" ? "#fafafa" : "text.primary",
          }}
        >
          {localized(content.title)}
        </Typography>
        <Typography
          id="release-spotlight-description"
          color="text.secondary"
          sx={{
            fontSize: { xs: ".94rem", sm: "1.05rem" },
            lineHeight: 1.6,
            maxWidth: 640,
          }}
        >
          {localized(content.description)}
        </Typography>
        {illustrations[content.image] && (
          <Box sx={{ mt: 1.5, mb: 3 }}>
            <Box
              component="img"
              src={illustrations[content.image]}
              alt={localized(content.image_alt)}
              width={1840}
              height={855}
              sx={{
                display: "block",
                width: "calc(100% + 24px)",
                maxWidth: "none",
                mx: "-12px",
                height: "auto",
                filter: "brightness(1.16) saturate(1.12)",
                position: "relative",
              }}
            />
            <Stack
              direction="row"
              justifyContent="center"
              gap={{ xs: 2, sm: 3 }}
              aria-hidden="true"
              sx={{ mt: 1.5 }}
            >
              {[
                "#ffbe50",
                "#64aafa",
                "#43d3a7",
                "#ff797c",
                "#a578ff",
                "#4cc8de",
              ].map((color) => (
                <Box
                  key={color}
                  sx={{
                    width: { xs: 16, sm: 22 },
                    height: { xs: 16, sm: 22 },
                    borderRadius: "50%",
                    bgcolor: color,
                    border: `1px solid ${alpha("#fff", 0.25)}`,
                    boxShadow: `0 2px 12px ${alpha(color, 0.22)}`,
                  }}
                />
              ))}
            </Stack>
          </Box>
        )}
        <Box sx={{ mt: 2.5 }}>
          {content.items.map((item, index) => {
            const Icon = icons[item.icon] || DashboardOutlinedIcon;
            return (
              <Stack
                key={index}
                direction="row"
                gap={2}
                sx={{ py: 2, borderTop: 1, borderColor: "divider" }}
              >
                <Box
                  sx={(theme) => ({
                    display: "grid",
                    placeItems: "center",
                    width: 48,
                    height: 48,
                    flexShrink: 0,
                    borderRadius: "10px",
                    bgcolor: alpha(theme.palette.primary.main, 0.13),
                    color: "primary.main",
                  })}
                >
                  <Icon sx={{ fontSize: 28 }} />
                </Box>
                <Box>
                  <Typography
                    component="h3"
                    sx={{ fontSize: "1rem", fontWeight: 650, mb: 0.4 }}
                  >
                    {localized(item.title)}
                  </Typography>
                  <Typography
                    color="text.secondary"
                    sx={{ fontSize: ".86rem", lineHeight: 1.6 }}
                  >
                    {localized(item.description)}
                  </Typography>
                </Box>
              </Stack>
            );
          })}
        </Box>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {t("releaseHighlights.saveFailed")}
          </Alert>
        )}
      </DialogContent>
      <DialogActions
        sx={{
          px: { xs: 2.5, sm: 4 },
          py: 2.5,
          gap: 1,
          flexWrap: "wrap",
          borderTop: 1,
          borderColor: "divider",
          "& > :not(style) ~ :not(style)": { ml: 0 },
        }}
      >
        <Button
          variant="contained"
          onClick={openAction}
          disabled={saving}
          endIcon={<ArrowForwardIcon />}
          sx={(theme) => ({
            "&&": {
              minHeight: 44,
              px: 2.5,
              fontWeight: 700,
              bgcolor: theme.palette.primary.main,
              color: theme.palette.getContrastText(theme.palette.primary.main),
              border: `1px solid ${lighten(theme.palette.primary.main, 0.25)}`,
              boxShadow: `0 3px 20px ${alpha(
                theme.palette.primary.main,
                0.19
              )}`,
              "&:hover": { bgcolor: lighten(theme.palette.primary.main, 0.12) },
            },
            flex: { xs: "1 1 100%", sm: "0 0 auto" },
          })}
        >
          {localized(content.action?.label) || t("releaseHighlights.done")}
        </Button>
        <Button
          variant="outlined"
          onClick={postpone}
          disabled={saving}
          sx={{
            minHeight: 44,
            px: 2.5,
            color: "text.primary",
            borderColor: "divider",
            bgcolor: "action.hover",
          }}
        >
          {t(saving ? "releaseHighlights.saving" : "releaseHighlights.later")}
        </Button>
        <Box sx={{ flexGrow: 1 }} />
        <Button
          onClick={() => {
            onClose();
            navigate(
              `/updates?release=${encodeURIComponent(release.tag_name)}`
            );
          }}
          disabled={saving}
          endIcon={<ArrowForwardIcon />}
          sx={{ color: "primary.main", minHeight: 44 }}
        >
          {t("releaseHighlights.allChanges")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
