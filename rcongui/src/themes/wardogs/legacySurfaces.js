import { alpha } from "@mui/material/styles";
import { fontFamily, geometry } from "./tokens";
import { pageLayouts } from "./pageLayouts";
import { surfaceHierarchy } from "./surfaceHierarchy";
import { wardogsBackground } from "./background";

// Older pages define their presentation with sx/styled instead of theme
// tokens. Keep the compatibility layer here and scoped to Wardogs, including
// portalled dialogs/menus. Frontline's existing selectors remain untouched.
export function legacySurfaces(theme) {
  const p = theme.palette;
  const raised = p.mode === "dark" ? "#1a1a1e" : "#f7f7f9";
  return {
    'html[data-theme-preset="wardogs"]': {
      "& body": { fontFamily },
      "& #main-content": { minWidth: 0, ...wardogsBackground(p.mode, theme.frontline?.appearance?.wardogsStyle) },
      "& [data-testid='desktop-header']": {
        "@media (max-width: 1499px)": {
          flexWrap: "wrap",
          gap: 10,
          "& > .MuiStack-root:first-of-type": {
            flex: "1 1 auto",
            minWidth: 200,
          },
          "& > [data-testid='global-match-status']": {
            order: 3,
            width: "100%",
            marginLeft: 0,
          },
          "& > .MuiStack-root:last-child": { marginLeft: 0 },
        },
      },
      "& #main-content > .MuiStack-root > .MuiContainer-root": {
        paddingTop: 24,
        paddingLeft: 24,
        paddingRight: 24,
        "@media (max-width: 599px)": { padding: 12 },
      },
      "& .MuiTypography-root:not(code):not(pre), & .MuiButtonBase-root, & input, & textarea, & select, & table":
        {
          fontFamily,
          letterSpacing: "normal",
          textTransform: "none",
        },
      "& .MuiTypography-root:is(h1, h2, h3, h4, h5, h6), & .MuiTypography-subtitle1, & .MuiTypography-subtitle2":
        {
          fontWeight: 500,
        },
      "& .MuiTypography-caption": { fontWeight: 400 },
      "& .MuiButton-root, & .MuiIconButton-root, & .MuiMenuItem-root, & .MuiListItemButton-root, & .MuiChip-root":
        {
          // Legacy navigation explicitly sets radius: 0 !important.
          borderRadius: "6px !important",
        },
      "& .MuiButton-root": { fontWeight: 500 },
      "& .MuiOutlinedInput-root": { borderRadius: "6px !important" },
      "& [data-testid='admin-action-context'], & [data-testid='general-settings-operations-matrix'] > .MuiBox-root, & [data-testid='general-settings-operations-matrix'] > .MuiStack-root":
        { borderRadius: 8, overflow: "hidden" },
      "& #server-rail-switcher-trigger": { borderRadius: "6px !important" },
      "& #appearance-dialog-title + .MuiDialogContent-root": { paddingTop: 20 },
      "& .MuiPaper-root:not(.MuiDrawer-paper):not(.MuiDialog-paper)": {
        borderRadius: 10,
        backgroundImage: "none",
      },
      "& .MuiDialog-paper": { borderRadius: 12 },
      "& .MuiDialog-paperFullScreen": { borderRadius: 0 },
      "& .MuiTooltip-tooltip": { borderRadius: "6px !important" },
      "& [data-testid='desktop-command-rail'] .MuiIconButton-root": {
        width: 42,
        height: 40,
      },
      "& [data-testid='desktop-command-rail'] .MuiIconButton-root::before": {
        width: 2,
        borderRadius: 2,
      },
      "& [data-testid='desktop-navigation-panel']": {
        "& .MuiList-root": { borderTop: 0, padding: 0, gap: 4 },
        "& .MuiListItemButton-root": {
          border: "1px solid transparent",
          minHeight: 40,
          padding: "6px 10px",
          "&[aria-current='page']": {
            borderColor: alpha(p.primary.main, 0.22),
            backgroundColor: alpha(p.primary.main, 0.12),
            color: p.primary.light,
          },
        },
        "& h2": { fontSize: 16, lineHeight: 1.5 },
      },
      "& [data-testid='wardogs-navigation-panel']": {
        "& .MuiListItemText-primary": {
          textTransform: "uppercase",
          fontSize: 12,
        },
        "& .MuiListItemButton-root[aria-current='page']": {
          borderColor: alpha(p.primary.main, 0.22),
          backgroundColor: alpha(p.primary.main, 0.12),
        },
      },
      "& [data-testid='global-match-status']": {
        border: `1px solid ${p.divider}`,
        borderRadius: 8,
        backgroundColor: p.background.paper,
        boxShadow: "none",
        "& .MuiTypography-caption": { letterSpacing: 0 },
        "& .MuiTypography-body2": { fontWeight: 500 },
      },
      "& [data-testid='page-header']": { paddingBottom: 16 },
      "& #main-content section[aria-labelledby], & #main-content section[aria-label]":
        {
          borderRadius: 10,
        },
      "& [data-testid='battle-overview']": {
        containerType: "inline-size",
        overflow: "hidden",
        "& > .MuiStack-root > :not(:last-child)": {
          width: "35%",
          minWidth: 0,
          maxWidth: 260,
        },
        "& .MuiStack-root > .MuiBox-root": { minWidth: 0 },
        "& .MuiTypography-caption": { whiteSpace: "normal" },
        "@container (max-width: 480px)": {
          "& > .MuiStack-root": { flexDirection: "column" },
          "& > .MuiStack-root > :not(:last-child)": {
            width: "100%",
            maxWidth: "none",
            height: 140,
            flexShrink: 0,
            borderRight: 0,
          },
        },
      },
      "& section[aria-labelledby='shift-situation-title'] .MuiButton-root": {
        minWidth: 0,
      },
      "& [data-testid='operations-overview'] section > .MuiStack-root:has(> .MuiStack-root > h2)":
        {
          backgroundColor: raised,
          borderRadius: "10px 10px 0 0",
        },
      "& [data-testid='live-players-panel'], & [data-testid='live-logs-panel'], & [data-testid='live-player-detail-panel']":
        {
          borderRadius: 10,
          overflow: "hidden",
          backgroundColor: p.background.paper,
        },
      "& [data-testid='live-status-cards'] > .MuiBox-root > *": {
        borderRadius: 8,
        borderWidth: 1,
        borderColor: p.divider,
        padding: 12,
      },
      "& [data-testid='live-balance-card']": {
        borderColor: p.divider,
        "& .MuiBox-root, & .MuiStack-root": { borderColor: p.divider },
        "& > .MuiStack-root:first-of-type": { backgroundColor: raised },
      },
      "& #main-content table": {
        fontFamily,
        borderColor: p.divider,
        "& thead, & th": {
          backgroundColor: raised,
          color: p.text.secondary,
          fontWeight: 500,
          borderColor: p.divider,
        },
        "& td": { borderColor: p.divider },
      },
      "& .MuiToggleButtonGroup-root": {
        backgroundColor: raised,
        borderRadius: 6,
      },
      "& .MuiToggleButton-root": {
        textTransform: "none",
        fontWeight: 500,
        borderColor: p.divider,
      },
      "& .MuiChip-root": { fontWeight: 500 },
      "& .MuiDrawer-paper": { backgroundImage: "none" },
      "& .Toastify__toast": {
        fontFamily,
        background: p.background.paper,
        color: p.text.primary,
        border: `1px solid ${p.divider}`,
        borderRadius: 10,
      },
      "& *": { scrollbarColor: `${p.text.disabled} ${p.background.default}` },
      "& *::selection": {
        color: p.primary.contrastText,
        background: p.primary.main,
      },
      ...pageLayouts(theme),
      // Explicit surface markers cover custom Box/Stack cards as well as MUI
      // panels. !important also overrides legacy page-level square selectors.
      "& [data-theme-surface='panel'], & [data-theme-surface='group'], & .MuiPaper-root:not(.MuiDrawer-paper):not(.MuiDialog-paperFullScreen)":
        {
          borderRadius: `${geometry.radius.structure}px !important`,
        },
      "& [data-theme-surface='group']": {
        overflow: "hidden",
        borderBottom: `1px solid ${p.divider}`,
      },
      "& [data-theme-surface='group'] > .MuiFormControlLabel-root": {
        borderColor: `${p.divider} !important`,
      },
      "& [data-theme-surface='control'], & .MuiPaginationItem-root, & .MuiAvatar-square, & .MuiAvatar-rounded":
        {
          borderRadius: `${geometry.radius.control}px !important`,
        },
      "& .MuiDialog-paperFullScreen": { borderRadius: "0 !important" },
      ...surfaceHierarchy(theme),
    },
  };
}
