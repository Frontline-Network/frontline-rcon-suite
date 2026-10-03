import {
  createElement,
  isValidElement,
  lazy,
  Suspense,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  Box,
  Collapse,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Popover,
  Stack,
  Tooltip,
  Typography,
  useMediaQuery,
} from "@mui/material";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import CloseIcon from "@mui/icons-material/Close";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import MonitorHeartOutlinedIcon from "@mui/icons-material/MonitorHeartOutlined";
import MenuOutlinedIcon from "@mui/icons-material/MenuOutlined";
import AddIcon from "@mui/icons-material/Add";
import PaletteOutlinedIcon from "@mui/icons-material/PaletteOutlined";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";
import { NavLink, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/hooks/useAuth";
import { useAppStore } from "@/stores/app-state";
import { COMMAND_RAIL_WIDTH } from "./CommandRail";
import { buildCommandRailWorkspaces } from "./command-rail-navigation";
import { doesNavigationRouteMatch } from "./command-rail-workspaces.mjs";
import ConnectionStatus from "../sidebar/ConnectionStatus";
import SystemUsage from "../sidebar/SystemUsage";
import ThemedBrandMark from "../ThemedBrandMark";
import { resolveWardogsShortcuts } from "./wardogs-shortcuts.mjs";

const WardogsShortcutsDialog = lazy(() => import("./WardogsShortcutsDialog"));

const icon = (value) =>
  value && (isValidElement(value) ? value : createElement(value));

// Wardogs presents the same permission-aware routes as a complete, grouped
// navigation tree. Frontline keeps its contextual workspace navigation.
export default function WardogsNavigation() {
  const { t } = useTranslation();
  const { permissions } = useAuth();
  const { pathname } = useLocation();
  const railVisible = useMediaQuery((theme) => theme.breakpoints.up("md"));
  const desktop = useMediaQuery("(min-width: 1280px)");
  const wide = useMediaQuery("(min-width: 1920px)");
  const panelWidth = wide ? 344 : 272;
  const open = useAppStore((state) => state.wardogsDrawerOpen);
  const setOpen = useAppStore((state) => state.setWardogsDrawerOpen);
  const setAppearanceOpen = useAppStore(
    (state) => state.setAppearanceDialogOpen
  );
  const [expanded, setExpanded] = useState({});
  const [healthAnchor, setHealthAnchor] = useState(null);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const savedShortcuts = useAppStore(
    (state) => state.appearance.wardogsShortcuts
  );
  const workspaces = useMemo(
    () =>
      buildCommandRailWorkspaces({
        pathname,
        permissions,
        includeLocked: true,
      }),
    [pathname, permissions]
  );
  const current = workspaces.find((workspace) => workspace.isActive);
  const shortcutOptions = useMemo(
    () => [
      ...new Map(
        workspaces.flatMap((workspace) =>
          workspace.sections.flatMap((section) =>
            section.links
              .filter((link) => !link.locked && link.to !== "/")
              .map((link) => [
                link.to,
                {
                  ...link,
                  label: link.translationKey
                    ? t(link.translationKey)
                    : link.name,
                  groupLabel: t(
                    section.labelTranslationKey || workspace.labelTranslationKey
                  ),
                  icon: icon(link.icon || workspace.icon),
                },
              ])
          )
        )
      ).values(),
    ],
    [workspaces, t]
  );
  const shortcuts = resolveWardogsShortcuts(savedShortcuts, shortcutOptions);
  const activeShortcut = shortcuts
    .filter((link) => doesNavigationRouteMatch(pathname, link.to))
    .sort((a, b) => b.to.length - a.to.length)[0]?.to;
  const currentId = current?.id;
  const currentLink = workspaces
    .flatMap((workspace) => workspace.links)
    .filter((link) => doesNavigationRouteMatch(pathname, link.to))
    .sort((a, b) => b.to.length - a.to.length)[0]?.to;

  useEffect(() => {
    if (currentId) setExpanded((value) => ({ ...value, [currentId]: true }));
  }, [currentId]);

  useEffect(() => {
    if (!desktop) setOpen(false);
  }, [desktop, setOpen]);

  const panel = (
    <Stack
      data-testid="wardogs-navigation-panel"
      sx={{
        width: panelWidth,
        maxWidth: "calc(100vw - 32px)",
        height: "100%",
        minHeight: 0,
        bgcolor: "background.paper",
        borderRight: "1px solid",
        borderColor: "divider",
      }}
    >
      <Stack
        direction="row"
        alignItems="center"
        spacing={1}
        sx={{ height: 64, px: 2.5, flexShrink: 0 }}
      >
        <Typography variant="overline" color="primary.main">
          FRONTLINE
        </Typography>
        <ChevronRightIcon sx={{ fontSize: 14, color: "text.disabled" }} />
        <Typography variant="overline">CRCON</Typography>
        {!desktop && (
          <IconButton
            aria-label={t("common.close")}
            onClick={() => setOpen(false)}
            sx={{ ml: "auto !important" }}
          >
            <CloseIcon fontSize="small" />
          </IconButton>
        )}
      </Stack>
      <List
        component="nav"
        aria-label={t("navigation.primary")}
        sx={{ flex: 1, overflowY: "auto", px: 1.5, py: 0, minHeight: 0 }}
      >
        {workspaces.map((workspace) => {
          const isExpanded = Boolean(expanded[workspace.id]);
          const direct = Boolean(workspace.directRoute);
          return (
            <Box key={workspace.id} sx={{ mb: 0.5 }}>
              <ListItemButton
                {...(direct
                  ? { component: NavLink, to: workspace.directRoute, end: true }
                  : {})}
                selected={direct && workspace.isActive}
                aria-current={direct && workspace.isActive ? "page" : undefined}
                aria-expanded={direct ? undefined : isExpanded}
                aria-controls={
                  direct ? undefined : `wardogs-group-${workspace.id}`
                }
                onClick={() =>
                  direct
                    ? !desktop && setOpen(false)
                    : setExpanded((value) => ({
                        ...value,
                        [workspace.id]: !isExpanded,
                      }))
                }
                sx={{
                  minHeight: 40,
                  px: 1.25,
                  border: "1px solid",
                  borderColor:
                    direct && workspace.isActive
                      ? "primary.dark"
                      : "transparent",
                  color:
                    direct && workspace.isActive
                      ? "primary.light"
                      : "text.secondary",
                }}
              >
                <ListItemIcon sx={{ minWidth: 30 }}>
                  {icon(workspace.icon)}
                </ListItemIcon>
                <ListItemText primary={t(workspace.labelTranslationKey)} />
                {!direct &&
                  (isExpanded ? (
                    <ExpandMoreIcon sx={{ fontSize: 17 }} />
                  ) : (
                    <ChevronRightIcon sx={{ fontSize: 17 }} />
                  ))}
              </ListItemButton>
              {!direct && (
                <Collapse in={isExpanded} unmountOnExit>
                  <List
                    id={`wardogs-group-${workspace.id}`}
                    disablePadding
                    sx={{
                      ml: 2.5,
                      my: 0.5,
                      pl: 1,
                      borderLeft: "1px solid",
                      borderColor: "divider",
                    }}
                  >
                    {workspace.sections.map((section) => (
                      <Box key={section.id}>
                        {workspace.sections.length > 1 && (
                          <Typography
                            variant="caption"
                            color="text.disabled"
                            sx={{ display: "block", px: 1, pt: 1, pb: 0.5 }}
                          >
                            {t(section.labelTranslationKey)}
                          </Typography>
                        )}
                        {section.links.filter((link) => link.to !== "/documentation").map((link) => (
                          <Tooltip
                            key={link.to}
                            title={
                              link.locked
                                ? t("navigation.permissionMissing")
                                : ""
                            }
                            placement="right"
                          >
                            <ListItemButton
                              {...(!link.locked
                                ? {
                                    component: NavLink,
                                    to: link.to,
                                    end: link.to === "/" || link.to === "/apps",
                                  }
                                : {})}
                              aria-disabled={link.locked || undefined}
                              aria-current={
                                currentLink === link.to ? "page" : undefined
                              }
                              selected={currentLink === link.to}
                              onClick={() =>
                                !link.locked && !desktop && setOpen(false)
                              }
                              sx={{
                                minHeight: 34,
                                px: 1.25,
                                py: 0.5,
                                color: link.locked
                                  ? "text.disabled"
                                  : currentLink === link.to
                                  ? "primary.light"
                                  : "text.secondary",
                                cursor: link.locked ? "not-allowed" : "pointer",
                              }}
                            >
                              <ListItemText
                                primary={
                                  link.translationKey
                                    ? t(link.translationKey)
                                    : link.name
                                }
                              />
                              {link.locked && (
                                <LockOutlinedIcon sx={{ fontSize: 14 }} />
                              )}
                            </ListItemButton>
                          </Tooltip>
                        ))}
                      </Box>
                    ))}
                  </List>
                </Collapse>
              )}
            </Box>
          );
        })}
      </List>
      <Box
        sx={{
          mx: 2.5,
          mt: 2,
          py: 2,
          borderTop: "1px solid",
          borderColor: "divider",
        }}
      >
        <ListItemButton component={NavLink} to="/documentation" selected={pathname === "/documentation"} onClick={() => !desktop && setOpen(false)}>
          <ListItemIcon sx={{ minWidth: 30 }}><MenuBookOutlinedIcon fontSize="small" /></ListItemIcon>
          <ListItemText primary={t("documentation.title")} />
        </ListItemButton>
        <ListItemButton
          onClick={(event) => setHealthAnchor(event.currentTarget)}
        >
          <ListItemIcon sx={{ minWidth: 30 }}>
            <MonitorHeartOutlinedIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText primary={t("sidebar.system")} />
        </ListItemButton>
        <ListItemButton onClick={() => setAppearanceOpen(true)}>
          <ListItemIcon sx={{ minWidth: 30 }}>
            <PaletteOutlinedIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText primary={t("appearance.title")} />
        </ListItemButton>
        <ListItemButton onClick={() => setShortcutsOpen(true)}>
          <ListItemIcon sx={{ minWidth: 30 }}>
            <AddIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText primary={t("navigation.shortcuts.title")} />
        </ListItemButton>
      </Box>
    </Stack>
  );

  return (
    <Box
      component="aside"
      sx={{
        display: railVisible ? "flex" : "none",
        height: "100dvh",
        flexShrink: 0,
        width: COMMAND_RAIL_WIDTH + (desktop && open ? panelWidth : 0),
      }}
    >
      {railVisible && (
        <Stack
          sx={{
            width: COMMAND_RAIL_WIDTH,
            flexShrink: 0,
            alignItems: "center",
            gap: 1.5,
            borderRight: "1px solid",
            borderColor: "divider",
            bgcolor: "background.default",
            minHeight: 0,
            pb: 1.5,
            "& > .MuiIconButton-root": { flexShrink: 0 },
          }}
        >
          <IconButton
            component={NavLink}
            to="/"
            aria-label="Frontline"
            sx={{ width: 52, height: 64, mb: 1 }}
          >
            <ThemedBrandMark sx={{ width: 40, height: 38 }} />
          </IconButton>
          <Tooltip title={t("navigation.primary")} placement="right">
            <IconButton
              onClick={() => setOpen(!open)}
              aria-label={t("navigation.toggleMenu")}
              color={open ? "primary" : "default"}
            >
              <MenuOutlinedIcon />
            </IconButton>
          </Tooltip>
          <Divider sx={{ width: 32, flexShrink: 0 }} />
          <Stack
            component="nav"
            aria-label={t("navigation.shortcuts.order")}
            data-testid="wardogs-shortcuts"
            sx={{
              minHeight: 0,
              overflowY: "auto",
              width: "100%",
              alignItems: "center",
              gap: 1.5,
              flexShrink: 1,
              px: 0.5,
            }}
          >
            {shortcuts.map((link) => (
              <Tooltip key={link.to} title={link.label} placement="right">
                <IconButton
                  component={NavLink}
                  to={link.to}
                  aria-label={link.label}
                  aria-current={activeShortcut === link.to ? "page" : undefined}
                  color={activeShortcut === link.to ? "primary" : "default"}
                  sx={{ flexShrink: 0, width: 44, height: 44 }}
                >
                  {link.icon}
                </IconButton>
              </Tooltip>
            ))}
          </Stack>
          <Tooltip title={t("navigation.shortcuts.title")} placement="right">
            <IconButton
              onClick={() => setShortcutsOpen(true)}
              aria-label={t("navigation.shortcuts.title")}
              sx={{
                flexDirection: "column",
                gap: 0.25,
                width: 48,
                minHeight: 56,
                border: "1px dashed",
                borderColor: "primary.dark",
                borderRadius: "10px",
                color: "primary.light",
                bgcolor: "action.selected",
                "&:hover": {
                  color: "primary.main",
                  borderColor: "primary.main",
                },
              }}
            >
              <AddIcon fontSize="small" />
              <Typography
                component="span"
                sx={{ fontSize: 10, lineHeight: 1.2 }}
              >
                {t("navigation.shortcuts.customize")}
              </Typography>
            </IconButton>
          </Tooltip>
        </Stack>
      )}
      {desktop ? (
        open && panel
      ) : (
        <Drawer
          open={open}
          onClose={() => setOpen(false)}
          ModalProps={{ keepMounted: true }}
        >
          {panel}
        </Drawer>
      )}
      <Popover
        open={Boolean(healthAnchor)}
        anchorEl={healthAnchor}
        onClose={() => setHealthAnchor(null)}
        anchorOrigin={{ vertical: "center", horizontal: "right" }}
        transformOrigin={{ vertical: "center", horizontal: "left" }}
      >
        <Box sx={{ width: 280, p: 2 }}>
          <Typography variant="h6">{t("sidebar.system")}</Typography>
          <List dense>
            <ConnectionStatus />
            <SystemUsage />
          </List>
        </Box>
      </Popover>
      {shortcutsOpen && (
        <Suspense fallback={null}>
          <WardogsShortcutsDialog
            links={shortcutOptions}
            onClose={() => setShortcutsOpen(false)}
          />
        </Suspense>
      )}
    </Box>
  );
}
