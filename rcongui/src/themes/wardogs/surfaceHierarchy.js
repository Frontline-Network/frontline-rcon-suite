// A panel owns its outer contour. Flush rows, table tools and plain layout
// wrappers must not acquire another rounded outline inside that same panel.
// These rules run after the legacy surface defaults and only within Wardogs.
export function surfaceHierarchy(theme) {
  const divider = `1px solid ${theme.palette.divider}`;
  const flush = { borderRadius: "0 !important" };

  return {
    "& [data-theme-surface='flush'], & .wardogs-page-tabs, & .wardogs-config-section[data-plain='true'], & .wardogs-profile-detail":
      flush,
    "& [data-theme-surface='table-toolbar']": {
      ...flush,
      border: 0,
      boxShadow: "none",
      "&:not([data-position='bottom'])": { borderBottom: divider },
    },
    "& [data-theme-surface='table-body']": {
      ...flush,
      border: 0,
      boxShadow: "none",
    },
    "& [data-theme-surface='field-group']": {
      ...flush,
      border: 0,
      backgroundColor: "transparent",
      padding: 0,
    },
    "& .wardogs-joined-table > :first-child": {
      borderRadius: "12px 12px 0 0 !important",
    },
    "& .wardogs-joined-table > :last-child": {
      borderRadius: "0 0 12px 12px !important",
    },
    "& .wardogs-table-pagination": {
      "@media (max-width: 599px)": {
        flexWrap: "wrap",
        width: "100%",
        justifyContent: "center",
        rowGap: 4,
        "& > .MuiDivider-root": { display: "none" },
        "& > .MuiBox-root:last-child": {
          flexBasis: "100%",
          margin: 0,
          "& .MuiInputBase-root": { width: "100%" },
        },
      },
    },
    "& .wardogs-map-workspace .wardogs-map-filter": {
      ...flush,
      border: 0,
      borderBottom: divider,
      backgroundColor: "transparent",
    },
    "& .wardogs-system-diagnostics .wardogs-config-grid, & .wardogs-system-diagnostics .wardogs-workbench > .wardogs-panel, & .wardogs-system-diagnostics .wardogs-action-bar":
      flush,
    // Joined buttons share a contour; only the group's outer corners curve.
    "& .MuiButtonGroup-root .MuiButtonGroup-grouped": flush,
    "& .MuiButtonGroup-root .MuiButtonGroup-firstButton": {
      borderTopLeftRadius: "6px !important",
      borderBottomLeftRadius: "6px !important",
    },
    "& .MuiButtonGroup-root .MuiButtonGroup-lastButton": {
      borderTopRightRadius: "6px !important",
      borderBottomRightRadius: "6px !important",
    },
  };
}
