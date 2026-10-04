import { useEffect, useMemo, useState } from "react";
import {
  Avatar,
  Box,
  ButtonBase,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  InputAdornment,
  List,
  ListItemButton,
  ListItemText,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import SearchOutlinedIcon from "@mui/icons-material/SearchOutlined";
import MenuOutlinedIcon from "@mui/icons-material/MenuOutlined";
import CloseOutlinedIcon from "@mui/icons-material/CloseOutlined";
import KeyboardArrowDownOutlinedIcon from "@mui/icons-material/KeyboardArrowDownOutlined";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/hooks/useAuth";
import { useAppStore } from "@/stores/app-state";
import { buildCommandRailWorkspaces } from "../navigation/command-rail-navigation";
import LanguageSelector from "../LanguageSelector";
import OptionsMenu from "../OptionsMenu";
import ServerStatus from "@/components/Header/server-status";

export default function WardogsToolbar() {
  const { t } = useTranslation();
  const { permissions } = useAuth();
  const navigate = useNavigate();
  const toggleDrawer = useAppStore((state) => state.toggleWardogsDrawer);
  const [searchOpen, setSearchOpen] = useState(false);
  const [search, setSearch] = useState("");
  const links = useMemo(
    () =>
      buildCommandRailWorkspaces({ permissions }).flatMap((workspace) =>
        workspace.links.map((link) => ({
          ...link,
          label: link.translationKey ? t(link.translationKey) : link.name,
          group: t(workspace.labelTranslationKey),
        }))
      ),
    [permissions, t]
  );
  const results = links.filter((link) =>
    `${link.label} ${link.group}`
      .toLocaleLowerCase()
      .includes(search.trim().toLocaleLowerCase())
  );
  useEffect(() => {
    const onKey = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearchOpen((open) => !open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  return (
    <>
      <Box
        data-testid="wardogs-toolbar"
        sx={{
          display: "grid",
          gridTemplateAreas: {
            xs: '"search tools" "status status"',
            md: '"search status tools"',
          },
          gridTemplateColumns: {
            xs: "minmax(0, 1fr) auto",
            md: "auto minmax(0, 1fr) auto",
          },
          gridTemplateRows: { xs: "56px 48px", md: "64px" },
          alignItems: "center",
          columnGap: { xs: 1, md: 2 },
          width: "100%",
          minWidth: 0,
          px: { xs: 1.5, md: "var(--wardogs-gutter)" },
          pt: { xs: "env(safe-area-inset-top)", md: 0 },
          pb: { xs: 1, md: 0 },
          position: { xs: "fixed", md: "relative" },
          top: 0,
          left: 0,
          zIndex: (theme) => theme.zIndex.appBar,
          bgcolor: { xs: "background.default", md: "transparent" },
        }}
      >
        <Stack
          direction="row"
          alignItems="center"
          gap={1}
          sx={{ gridArea: "search", minWidth: 0 }}
        >
          <IconButton
            sx={{ display: { xs: "inline-flex", lg: "none" } }}
            aria-label={t("navigation.toggleMenu")}
            onClick={toggleDrawer}
            size="small"
          >
            <MenuOutlinedIcon fontSize="small" />
          </IconButton>
          <ButtonBase
            onClick={() => setSearchOpen(true)}
            aria-label={t("common.search")}
            sx={{ color: "text.secondary", gap: 1.25, py: 1, px: 0.5 }}
          >
            <SearchOutlinedIcon sx={{ fontSize: 19 }} />
            <Typography variant="body2">{t("common.search")}</Typography>
            <Typography
              variant="caption"
              sx={{
                ml: 2,
                display: { xs: "none", lg: "block" },
                color: "text.disabled",
              }}
            >
              Ctrl K
            </Typography>
          </ButtonBase>
        </Stack>
        <Box sx={{ gridArea: "status", minWidth: 0 }}>
          <ServerStatus variant="toolbar" />
        </Box>
        <Stack
          direction="row"
          alignItems="center"
          gap={1}
          sx={{ gridArea: "tools" }}
        >
          <LanguageSelector />
          <OptionsMenu
            renderTrigger={(props) => (
              <ButtonBase {...props} sx={{ gap: 1, p: 0.75 }}>
                <Avatar
                  sx={{
                    width: 30,
                    height: 30,
                    bgcolor: "primary.dark",
                    color: "primary.contrastText",
                    fontSize: 12,
                  }}
                >
                  {(permissions?.user_name || "?").slice(0, 1).toUpperCase()}
                </Avatar>
                <KeyboardArrowDownOutlinedIcon sx={{ fontSize: 16 }} />
              </ButtonBase>
            )}
          />
        </Stack>
      </Box>
      <Dialog
        open={searchOpen}
        onClose={() => setSearchOpen(false)}
        fullWidth
        maxWidth="sm"
        aria-labelledby="wardogs-search-title"
      >
        <DialogTitle
          id="wardogs-search-title"
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          {t("navigation.navigateTo")}
          <IconButton
            onClick={() => setSearchOpen(false)}
            aria-label={t("common.close")}
          >
            <CloseOutlinedIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            value={search}
            placeholder={t("common.search")}
            inputProps={{ "aria-label": t("common.search") }}
            onChange={(event) => setSearch(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && results[0]) {
                navigate(results[0].to);
                setSearchOpen(false);
              }
            }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchOutlinedIcon />
                </InputAdornment>
              ),
            }}
          />
          <List sx={{ maxHeight: "50vh", overflow: "auto", mt: 1 }}>
            {results.map((link) => (
              <ListItemButton
                key={link.to}
                component={Link}
                to={link.to}
                onClick={() => setSearchOpen(false)}
              >
                <ListItemText primary={link.label} secondary={link.group} />
              </ListItemButton>
            ))}
            {!results.length && (
              <Typography color="text.secondary" sx={{ p: 2 }}>
                {t("common.noResults")}
              </Typography>
            )}
          </List>
        </DialogContent>
      </Dialog>
    </>
  );
}
