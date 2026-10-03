// Layout rules target named page primitives, so Wardogs can evolve independently
// of Frontline's dense operational workspaces.
export function pageLayouts(theme) {
  const p = theme.palette;
  const raised = p.mode === "dark" ? "#18181b" : "#f3f3f5";
  const panel = {
    border: `1px solid ${p.divider}`,
    borderRadius: 12,
    overflow: "hidden",
    backgroundColor: p.background.paper,
  };
  const panelHeader = {
    padding: "20px 24px",
    backgroundColor: raised,
    borderBottom: `1px solid ${p.divider}`,
  };
  return {
    "& .wardogs-live-statistics": {
      gap: 20,
      "& > *": { marginTop: "0 !important" },
      "& > .MuiBox-root:has(> .MuiToggleButtonGroup-root), & > .MuiBox-root:has(> .MuiBox-root > .MuiStack-root)":
        panel,
      "& .MuiBox-root, & .MuiStack-root": { borderColor: p.divider },
    },
    "& .wardogs-live-team-table": { ...panel, overflowX: "auto" },
    "& .wardogs-login-image, & .wardogs-login-hero": { display: "none" },
    "& .wardogs-login": {
      alignItems: "center",
      justifyContent: "center",
      padding: 24,
      minHeight: "100dvh",
      backgroundColor: p.background.default,
    },
    "& .wardogs-login-card": {
      ...panel,
      flex: "0 1 440px",
      width: "100%",
      maxWidth: 440,
      "& > .MuiStack-root:first-of-type": {
        padding: 24,
        borderBottom: `1px solid ${p.divider}`,
      },
      "& > main": { padding: 32, width: "100%", maxWidth: "none" },
      "& > main > .MuiBox-root, & form": { width: "100%" },
      "& h1": { fontSize: 28, marginBottom: 12 },
      "@media (max-width: 899px)": { flex: "0 1 auto" },
    },
    "& .wardogs-completed-game": {
      padding: 0,
      "& > .MuiStack-root": { gap: 24 },
      "& h1": { color: p.text.primary, marginBottom: 20 },
      "& section > .MuiBox-root": { borderRadius: 12, borderColor: p.divider },
      "& .MuiBox-root, & .MuiStack-root": { borderColor: p.divider },
    },
    "& .wardogs-page-tabs": {
      border: 0,
      borderBottom: `1px solid ${p.divider}`,
      backgroundColor: "transparent",
      marginBottom: 24,
      "& .MuiTabs-root": {
        marginBottom: "0 !important",
        borderBottom: "0 !important",
      },
      "& .MuiTab-root, & > .MuiButtonBase-root": {
        borderRight: 0,
        minHeight: 52,
        padding: "10px 18px",
      },
    },
    "& .wardogs-map-workspace": {
      border: 0,
      backgroundColor: "transparent",
      marginTop: 0,
      "& section": panel,
      "& section > .MuiStack-root:first-of-type, & section > .MuiBox-root:first-of-type:has(h2)":
        panelHeader,
      "& .MuiAccordion-root": { borderRadius: "12px !important" },
      "& > .MuiBox-root:first-of-type": { padding: 0 },
    },
    "& [data-testid='integration-config-editor']": {
      border: 0,
      backgroundColor: "transparent",
      gap: 20,
      "& > section": {
        ...panel,
        padding: 24,
        gridColumn: "1 / -1",
        "@media (min-width: 1800px)": { gridColumn: "span 6" },
      },
      "& > section > .MuiStack-root:first-of-type": { marginBottom: 24 },
      "& .MuiBox-root": { borderColor: p.divider },
    },
    "& .wardogs-config-fields .MuiBox-root, & .wardogs-autobalancer .MuiBox-root, & .wardogs-autobalancer .MuiStack-root":
      {
        borderColor: p.divider,
      },
    "& .wardogs-autobalancer > .MuiStack-root:first-of-type": {
      marginBottom: 24,
    },
    "& .wardogs-player-profile": {
      minHeight: 0,
      "& > section:first-of-type": {
        backgroundColor: "transparent",
        border: 0,
        padding: 0,
        marginBottom: 0,
      },
      "& > section:first-of-type > .MuiCardContent-root": {
        padding: "0 0 24px",
      },
      "& .MuiTabs-root": {
        overflow: "hidden",
        "& .MuiTab-root": { minWidth: 0 },
      },
    },
    "& .wardogs-profile-grid": {
      gap: 24,
      alignItems: "start",
      gridTemplateColumns: "minmax(0, 1fr)",
      "@media (min-width: 1600px)": {
        gridTemplateColumns: "300px minmax(0, 1fr)",
      },
      "& > section": { minWidth: 0, padding: 0, height: "auto" },
      "& > section > .MuiCardContent-root": { padding: 24 },
    },
    "& .wardogs-app-page": {
      paddingTop: 0,
      "& > .MuiTypography-overline": { display: "none" },
      "& .MuiCard-root": {
        background: p.background.paper,
        borderColor: p.divider,
      },
    },
    "& .wardogs-page-content > .MuiBox-root, & .wardogs-page-content > .MuiStack-root, & .wardogs-workbench, & [data-testid='integrations-hub']":
      {
        width: "100%",
        maxWidth: "none",
        marginLeft: 0,
        marginRight: 0,
      },
    "& .wardogs-panel, & .wardogs-filter-panel, & .wardogs-player-filters":
      panel,
    "& .wardogs-journal": {
      ...panel,
      borderRadius: "12px 12px 0 0",
      "& > .MuiBox-root:first-of-type": panelHeader,
    },
    "& .wardogs-filter-panel > .MuiBox-root:first-of-type, & .wardogs-player-filters":
      { padding: 20 },
    "& .wardogs-workbench > .wardogs-panel > section": {
      padding: 28,
      "@media (max-width: 599px)": { padding: 16 },
    },
    "& .wardogs-workbench > .MuiBox-root > footer": {
      borderRadius: "12px !important",
      borderTop: `1px solid ${p.divider} !important`,
      boxShadow: "none",
    },
    "& .wardogs-workbench .MuiBox-root, & .wardogs-workbench .MuiStack-root": {
      borderColor: p.divider,
    },
    "& .wardogs-workbench aside": {
      borderRadius: 10,
      overflow: "hidden",
      backgroundColor: raised,
    },
    "& .wardogs-blacklist-layout": {
      gridTemplateColumns: "minmax(0, 1fr)",
      gap: 24,
    },
    "& .wardogs-blacklist-filters": {
      ...panel,
      position: "static",
      padding: 20,
    },
    "& .wardogs-blacklist-filter-fields": {
      display: "grid",
      gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
      alignItems: "center",
      gap: 12,
      "& > .MuiStack-root": {
        flexDirection: "row",
        gap: 4,
        gridColumn: "1 / 2",
      },
      "& > .MuiTypography-caption": { display: "none" },
      "& > .MuiButton-root": { marginTop: 0 },
      "& > .MuiFormControl-root:last-child": { gridColumn: "3", gridRow: "3" },
      "@media (max-width: 899px)": {
        gridTemplateColumns: "minmax(0, 1fr)",
        "& > .MuiFormControl-root:last-child": {
          gridColumn: "auto",
          gridRow: "auto",
        },
      },
    },
    "& #main-content > .MuiStack-root > .MuiContainer-root": {
      padding: "18px var(--wardogs-gutter) 0",
      "@media (max-width: 899px)": { padding: "20px 16px 0" },
    },
    "& .wardogs-page-context .MuiBreadcrumbs-root": {
      margin: "0 0 7px",
      "& .MuiTypography-root": { fontSize: 12, fontWeight: 400 },
      "& svg": { fontSize: 15 },
    },
    "& .wardogs-page-content h1": {
      fontSize: "28px",
      lineHeight: 1.3,
      fontWeight: 600,
      letterSpacing: 0,
    },
    "& .wardogs-page-content > *, & .wardogs-page-content > * > [data-testid$='workbench']":
      { minWidth: 0 },
    "& [data-testid='page-header'], & .wardogs-page-content header:has(h1)": {
      padding: "0 0 26px",
      marginBottom: 0,
      borderBottom: 0,
      "& .MuiTypography-overline": { display: "none" },
      "& h1 + .MuiTypography-root": {
        marginTop: 8,
        fontSize: 14,
        maxWidth: 960,
      },
    },
    "& .wardogs-page-content > .MuiBox-root:has(> [data-testid='page-header'])":
      { paddingTop: 0 },
    "& .wardogs-page-content .MuiTabs-root": {
      marginBottom: 20,
      minHeight: 44,
      borderBottom: `1px solid ${p.divider}`,
      backgroundColor: "transparent",
      "& .MuiTab-root": {
        minHeight: 44,
        padding: "10px 18px",
        fontWeight: 500,
      },
    },
    "& .wardogs-page-content .MuiTableContainer-root": panel,
    "& .wardogs-page-content .MuiAccordion-root": {
      ...panel,
      marginBottom: 12,
      "&::before": { display: "none" },
      "& .MuiAccordionSummary-root": { minHeight: 56 },
    },
    "& [data-page-family='maps'] [data-testid$='workbench']": {
      width: "100%",
      maxWidth: "none",
      margin: 0,
    },
    "& .wardogs-builder-panel": panel,
    "& .MuiOutlinedInput-notchedOutline": { borderRadius: "6px !important" },
    "& .wardogs-builder-panel > .MuiStack-root, & .wardogs-map-catalog > .MuiStack-root":
      panelHeader,
    "& .wardogs-map-catalog": panel,
    "& .wardogs-map-filter": {
      padding: 24,
      backgroundColor: "transparent",
      borderRadius: 0,
      containerType: "inline-size",
      containerName: "wardogs-map-filter",
    },
    "& .wardogs-map-filter > .MuiBox-root": {
      gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
      gap: 12,
      "& > .MuiTextField-root": { gridColumn: "1 / -1" },
      "@container wardogs-map-filter (min-width: 900px)": {
        gridTemplateColumns:
          "minmax(220px, 2fr) minmax(150px, 1fr) minmax(150px, 1fr) auto",
        "& > .MuiTextField-root": { gridColumn: "auto" },
      },
      "@container wardogs-map-filter (max-width: 480px)": {
        gridTemplateColumns: "minmax(0, 1fr)",
      },
    },
    "& .wardogs-map-list-row": {
      border: 0,
      borderBottom: `1px solid ${p.divider}`,
      borderRadius: 0,
      marginBottom: 0,
      padding: "12px 16px",
      minHeight: 78,
      "&:last-child": { borderBottom: 0 },
    },
    "& .wardogs-map-list-row .MuiIconButton-root": {
      backgroundColor: raised,
      color: p.text.primary,
      border: `1px solid ${p.divider}`,
      "&:hover": { backgroundColor: p.action.selected, color: p.primary.main },
    },
    "& .wardogs-control-layout": { ...panel, display: "block" },
    "& .wardogs-control-layout > .MuiFormControl-root": {
      padding: 0,
      margin: 16,
      width: "calc(100% - 32px)",
      "& > .MuiInputLabel-root": { marginLeft: 0 },
    },
    "& .wardogs-map-summary-metric, & [data-testid='votemap-effect-summary'] > *":
      {
        borderColor: p.divider,
      },
    "& .wardogs-control-navigation": {
      borderRight: 0,
      display: "flex",
      flexDirection: "row",
      flexWrap: "wrap",
      gap: 4,
      padding: 12,
      borderBottom: `1px solid ${p.divider}`,
      backgroundColor: raised,
      "& .MuiButton-root": {
        minHeight: 38,
        border: 0,
        padding: "8px 14px",
        fontWeight: 500,
      },
    },
    "& .wardogs-control-header": panelHeader,
    "& .wardogs-control-row": {
      padding: "22px 24px",
      gap: 24,
      gridTemplateColumns: "minmax(200px, 1fr) minmax(0, 1.35fr) 140px",
      "& > *": { padding: 0 },
      "@media (max-width: 1399px)": { display: "flex", alignItems: "stretch" },
    },
    "& .wardogs-action-bar": {
      ...panel,
      marginTop: 20,
      padding: "16px 24px",
      boxShadow: "none",
      borderTop: `1px solid ${p.divider}`,
      "@media (max-width: 599px)": {
        padding: 16,
        marginLeft: 0,
        marginRight: 0,
      },
    },
    "& .wardogs-config-layout": { width: "100%", maxWidth: "none", margin: 0 },
    "& .wardogs-config-layout > .MuiStack-root": { marginBottom: 24 },
    "& .wardogs-config-layout > .MuiStack-root:empty": { display: "none" },
    "& .wardogs-config-grid": {
      ...panel,
      gap: 0,
      minHeight: 0,
      gridTemplateColumns: "minmax(0, 1fr) 280px",
      gridTemplateAreas: '"navigation navigation" "content summary"',
      "@media (max-width: 1399px)": {
        gridTemplateColumns: "minmax(0, 1fr)",
        gridTemplateAreas: '"navigation" "content" "summary"',
      },
    },
    "& .wardogs-config-grid[data-has-summary='false']": {
      gridTemplateColumns: "minmax(0, 1fr)",
      gridTemplateAreas: '"navigation" "content"',
    },
    "& .wardogs-config-grid > .wardogs-config-nav": {
      borderRight: 0,
      borderBottom: `1px solid ${p.divider}`,
      backgroundColor: raised,
    },
    "& .wardogs-config-grid > .wardogs-config-fields": { padding: 24 },
    "& .wardogs-config-grid > .wardogs-config-summary": {
      padding: 24,
      backgroundColor: raised,
      "@media (max-width: 1399px)": {
        borderLeft: 0,
        borderTop: `1px solid ${p.divider}`,
      },
    },
    "& .wardogs-config-section-tabs": {
      margin: "0 !important",
      borderBottom: "0 !important",
      padding: "4px 12px",
    },
    "& [data-page-family='records'] #players-section": { ...panel, gap: 0 },
    "& [data-page-family='records'] #players-section > .MuiStack-root:first-of-type":
      { ...panelHeader, border: 0, borderRadius: 0 },
    "& [data-page-family='records'] #players-section > .MuiBox-root": {
      marginTop: 0,
    },
    "& [data-page-family='records'] #players-section > .MuiStack-root:last-child":
      { padding: 16 },
    "& .wardogs-page-content [data-testid='live-status-cards']": {
      marginBottom: 24,
    },
    "& .wardogs-page-content [data-testid='live-players-panel'], & .wardogs-page-content [data-testid='live-logs-panel']":
      { ...panel, "& table td": { paddingTop: 10, paddingBottom: 10 } },
    "& .wardogs-page-content [data-testid='live-balance-card']": {
      ...panel,
      marginBottom: 24,
    },
    "& [data-testid='operations-overview']": { gap: 24 },
    "& [data-testid='operations-overview'] > .MuiBox-root": {
      marginTop: 0,
      gap: 24,
    },
    "& [data-testid='operations-overview'] section": panel,
    "& [data-testid='operations-overview'] section > .MuiStack-root:has(> .MuiStack-root > h2)":
      panelHeader,
    "& [data-testid='operations-overview'] .wardogs-dashboard-top": {
      display: "grid",
      gridTemplateColumns: "minmax(0, 1.25fr) minmax(0, 1fr)",
      "@media (max-width: 1199px)": { gridTemplateColumns: "minmax(0, 1fr)" },
    },
    "& [data-testid='operations-overview'] .wardogs-dashboard-top > [data-testid='battle-overview']":
      { order: -1 },
    "& [data-testid='operations-overview'] .wardogs-dashboard-top > section": {
      minHeight: 240,
    },
    "& [data-testid='operations-overview'] .wardogs-dashboard-detail": {
      alignItems: "start",
      gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)",
      "@media (max-width: 1399px)": { gridTemplateColumns: "minmax(0, 1fr)" },
    },
    "& [data-testid='operations-overview'] .wardogs-dashboard-detail > .MuiStack-root":
      { gap: 24, "& > *": { marginTop: 0 } },
    "& [data-testid='operations-overview'] #shift-situation-title + .MuiTypography-root":
      { fontSize: 24 },
    "& [data-testid='operations-overview'] section[aria-labelledby='shift-situation-title']":
      { padding: 28 },
    "& .wardogs-campaign-workspace": {
      ...panel,
      gridTemplateColumns: "minmax(0, 1fr)",
      minHeight: 0,
      "@media (min-width: 1000px)": {
        gridTemplateColumns: "240px minmax(0, 1fr)",
      },
    },
    "& .MuiCard-root:has(> .wardogs-campaign-editor)": { padding: 0 },
    "& .wardogs-campaign-editor": {
      containerType: "inline-size",
      containerName: "wardogs-campaign-editor",
      padding: "24px !important",
      "& > .MuiStack-root": { gap: 24, "& > *": { marginTop: 0 } },
    },
    "& .wardogs-campaign-header": {
      flexWrap: "wrap",
      gap: 16,
      "& > .MuiStack-root:first-of-type": { flex: "1 1 280px" },
      "& > .MuiStack-root:last-of-type": { marginLeft: "auto" },
      "@container wardogs-campaign-editor (max-width: 480px)": {
        flexDirection: "column",
        alignItems: "stretch",
        "& > .MuiStack-root:first-of-type": { flexBasis: "auto" },
      },
    },
    "& .wardogs-campaign-fields": {
      display: "grid",
      gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
      gap: "24px 16px",
      alignItems: "start",
      "& > .MuiFormControl-root": { minWidth: 0, width: "100%" },
      "& > .MuiFormControlLabel-root": {
        margin: 0,
        minHeight: 42,
        gridColumn: "1 / -1",
      },
      "@container wardogs-campaign-editor (max-width: 420px)": {
        gridTemplateColumns: "minmax(0, 1fr)",
      },
    },
    "& .wardogs-config-section[data-plain='true'] > .MuiCardContent-root": {
      paddingTop: 20,
    },
    "& .wardogs-campaign-fields[data-delivery-mode='player_message'] > .MuiFormControl-root:first-of-type":
      {
        gridColumn: "1 / -1",
      },
    "& .wardogs-config-section h2": { textTransform: "none", letterSpacing: 0 },
    "& .wardogs-system-diagnostics .wardogs-config-grid": {
      border: 0,
      borderRadius: 0,
    },
    "& .wardogs-system-diagnostics .wardogs-workbench": {
      padding: 0,
      "& > header:empty": { display: "none" },
      "& > header:not(:empty)": { padding: "16px 24px 0", marginBottom: 0 },
      "& > .wardogs-panel": { border: 0, borderRadius: 0 },
      "& > .MuiBox-root > footer": {
        borderRadius: "0 !important",
        borderWidth: "1px 0 0",
      },
    },
    "& .wardogs-system-diagnostics .wardogs-action-bar": {
      borderRadius: 0,
      borderWidth: "1px 0 0",
      marginTop: 0,
    },
    "& .wardogs-control-action-status": { flex: "1 1 auto" },
    "& .wardogs-action-content": { gap: "16px 24px" },
    "& .wardogs-action-status": { flex: "1 1 auto" },
    "& .wardogs-action-buttons": {
      flexWrap: "wrap",
      justifyContent: "flex-end",
      "@media (max-width: 599px)": {
        gridTemplateColumns: "minmax(0, 1fr)",
        "& .MuiButton-root": { whiteSpace: "normal", lineHeight: 1.4 },
      },
    },
    "& .wardogs-action-bar .MuiButton-root": { minHeight: 40 },
    "& .wardogs-writing-guide": {
      borderRadius: 10,
      backgroundColor: raised,
      alignSelf: "start",
    },
    "& .wardogs-template-workspace": {
      gap: 24,
      alignItems: "start",
      "& > aside": { ...panel, width: 304, minWidth: 0 },
      "& > aside > .MuiStack-root:first-of-type": { padding: 16 },
      "& > aside .MuiListItemButton-root": {
        padding: "12px 16px",
        minHeight: 64,
      },
      "& > form > .MuiPaper-root": panel,
      "& > form > .MuiPaper-root > .MuiStack-root:first-of-type": panelHeader,
      "& > form > .MuiPaper-root > .MuiBox-root": { padding: 24 },
      "@media (max-width: 899px)": { "& > aside": { width: "100%" } },
    },
    "& .wardogs-summary-strip": {
      ...panel,
      marginBottom: 24,
      "& > *": { borderColor: p.divider },
    },
    "& .wardogs-autosettings": {
      gap: 24,
      "& > .MuiPaper-root": { ...panel, padding: 20, marginBottom: 0 },
      "& > section > .MuiBox-root": panel,
    },
    "& .monaco-editor, & .monaco-editor-background, & .monaco-editor .margin": {
      backgroundColor: `${p.background.paper} !important`,
    },
    "& .wardogs-profanity-workspace": {
      ...panel,
      "& aside": {
        backgroundColor: raised,
        borderColor: p.divider,
        padding: 24,
      },
      "& > .MuiBox-root > .MuiBox-root": { padding: 24 },
    },
    "& .wardogs-vip-workspace": {
      gap: 24,
      "& > .MuiBox-root:first-of-type > .MuiBox-root": {
        ...panel,
        padding: 20,
      },
    },
    "& .wardogs-app-catalog .MuiCard-root": {
      padding: 0,
      "& > .MuiCardContent-root": { height: "100%", padding: 24 },
      "& > .MuiCardContent-root > .MuiStack-root": { height: "100%" },
      "& > .MuiCardContent-root > .MuiStack-root > :last-child": {
        marginTop: "auto",
        paddingTop: 0,
      },
      "& > .MuiCardContent-root > .MuiStack-root > .MuiTypography-root": {
        marginBottom: 24,
      },
    },
    "& .wardogs-profile-detail": {
      border: 0,
      padding: 0,
      borderRadius: 0,
      "& > .MuiCardContent-root": { padding: 0 },
    },
    "& .wardogs-profile-filters": {
      padding: "8px 0 16px",
      display: "grid",
      gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
      gap: 16,
      "& .MuiTextField-root": { minWidth: 0, maxWidth: "none" },
      "& > .MuiTextField-root:only-child": { gridColumn: "1 / -1" },
      "@media (max-width: 599px)": { gridTemplateColumns: "minmax(0, 1fr)" },
      "& .date-inputs": {
        display: "grid",
        gridColumn: "1 / -1",
        gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 230px), 1fr))",
        gap: 16,
      },
    },
    "& .wardogs-profile-scroll": {
      height: "auto",
      minHeight: 0,
      maxHeight: "65dvh",
      padding: 0,
      "& > .MuiBox-root": { padding: "16px 0" },
      "@media (max-width: 599px)": {
        "& > .MuiBox-root": { gridTemplateColumns: "minmax(0, 1fr)", gap: 8 },
      },
    },
    "& form > .wardogs-profile-filters": {
      gridTemplateColumns: "minmax(0, 1fr) auto",
      alignItems: "center",
      "& > .MuiButton-root": { minWidth: 180, minHeight: 40 },
      "@media (max-width: 599px)": {
        gridTemplateColumns: "minmax(0, 1fr)",
        "& > .MuiButton-root": { minHeight: 44 },
      },
    },
    "@media (max-width: 599px)": {
      "& .wardogs-page-content h1": { fontSize: 25 },
      "& .wardogs-map-filter, & .wardogs-config-grid > .wardogs-config-fields, & .wardogs-config-grid > .wardogs-config-summary":
        { padding: 16 },
      "& .wardogs-control-row, & .wardogs-control-header, & .wardogs-map-catalog > .MuiStack-root":
        { padding: 16 },
      "& .wardogs-profile-grid > section > .MuiCardContent-root, & .wardogs-template-workspace > form > .MuiPaper-root > .MuiBox-root, & .wardogs-profanity-workspace aside":
        { padding: 16 },
      "& .wardogs-campaign-editor": { padding: "16px !important" },
    },
  };
}
