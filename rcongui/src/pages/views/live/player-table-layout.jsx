import { Box, styled } from "@mui/material";

export const PLAYER_TABLE_LAYOUT = Object.freeze({
  desktopRowHeight: 38,
  tabletRowHeight: 44,
  touchRowHeight: 48,
  headerHeight: 40,
});

/**
 * Adds the responsive scroll and density contract for the live player table.
 *
 * This component deliberately wraps only <Table />. The shared Table component
 * renders its optional top scrollbar and its table viewport as direct children,
 * which lets this layout stay isolated from the live log and other tables.
 */
export const PlayerTableLayout = styled(Box, {
  name: "PlayerTableLayout",
  slot: "Root",
})(({ theme }) => ({
  "--player-table-row-height": `${PLAYER_TABLE_LAYOUT.touchRowHeight}px`,
  "--player-table-header-height": `${PLAYER_TABLE_LAYOUT.headerHeight}px`,
  "--player-table-max-height": "clamp(22rem, calc(100dvh - 15rem), 36rem)",
  minWidth: 0,
  position: "relative",

  // Table's synchronized horizontal scrollbar remains visible above the
  // vertically scrolling rows, instead of being available after player 100.
  "&& > [role='region']": {
    position: "relative",
    zIndex: 8,
    backgroundColor: theme.palette.background.paper,
  },

  // Table currently owns horizontal scrolling. This wrapper adds only the
  // player-specific vertical viewport and intentionally leaves logs untouched.
  "&& > :last-child": {
    maxHeight: "var(--player-table-max-height)",
    overflowX: "auto",
    overflowY: "auto",
    overscrollBehavior: "contain",
    // Do not reserve an empty scrollbar column when fewer players are shown.
    // Native overlay/auto scrollbars keep the detail row flush with the table.
    scrollbarGutter: "auto",
    WebkitOverflowScrolling: "touch",
    isolation: "isolate",
  },

  "& table": {
    borderCollapse: "separate",
    borderSpacing: 0,
  },

  // Apply sticky positioning to every header cell. Existing sticky left/right
  // metadata still works because top and the horizontal inset can coexist.
  "& thead th": {
    position: "sticky",
    top: 0,
    zIndex: 6,
    boxSizing: "border-box",
    height: "var(--player-table-header-height)",
    minHeight: "var(--player-table-header-height)",
    backgroundColor: theme.palette.background.paper,
    boxShadow: `inset 0 -1px 0 ${theme.palette.divider}`,
    whiteSpace: "nowrap",
  },

  // A sticky corner cell must remain above both the scrolling header and body
  // cells. The first three player columns are selection, disclosure and name.
  "& thead th:nth-of-type(-n + 3)": {
    zIndex: 9,
  },

  "& tbody td:not([colspan])": {
    boxSizing: "border-box",
    height: "var(--player-table-row-height)",
    minHeight: "var(--player-table-row-height)",
    maxHeight: "var(--player-table-row-height)",
    paddingTop: "0 !important",
    paddingBottom: "0 !important",
    verticalAlign: "middle",
    whiteSpace: "nowrap",
  },

  "& tbody td:not([colspan]) .MuiStack-root": {
    minWidth: 0,
    flexWrap: "nowrap",
  },

  "& tbody td:not([colspan]) .MuiTypography-root": {
    minWidth: 0,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },

  // Expanded player details are exempt from the compact one-line row contract.
  "& tbody td[colspan]": {
    height: "auto",
    maxHeight: "none",
    padding: "0 !important",
    whiteSpace: "normal",
    backgroundColor: theme.palette.background.paper,
  },

  // Touch widths intentionally trade row density for reliable controls.
  "& tbody td:not([colspan]) .MuiIconButton-root, & tbody td:not([colspan]) .MuiCheckbox-root":
    {
      minWidth: 44,
      minHeight: 44,
    },

  [theme.breakpoints.up("sm")]: {
    "--player-table-row-height": `${PLAYER_TABLE_LAYOUT.tabletRowHeight}px`,
    "--player-table-max-height": "clamp(24rem, 60dvh, 40rem)",
  },

  [theme.breakpoints.up("lg")]: {
    "--player-table-row-height": `${PLAYER_TABLE_LAYOUT.desktopRowHeight}px`,
    "--player-table-max-height": "clamp(26rem, calc(100dvh - 20rem), 48rem)",

    "& tbody td:not([colspan]) .MuiIconButton-root, & tbody td:not([colspan]) .MuiCheckbox-root":
      {
        minWidth: 32,
        minHeight: 32,
      },
  },

  "@media (prefers-reduced-motion: reduce)": {
    "&& > :last-child": {
      scrollBehavior: "auto",
    },
  },
}));

export default PlayerTableLayout;
