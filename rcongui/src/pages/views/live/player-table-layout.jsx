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
  containerType: "inline-size",
  minWidth: 0,
  position: "relative",

  // Table's synchronized horizontal scrollbar remains visible above the
  // vertically scrolling rows, instead of being available after player 100.
  "&& > [role='region']": {
    position: "relative",
    zIndex: 8,
    backgroundColor: theme.palette.background.paper,
  },

  // Wide expert columns may still scroll horizontally. Vertically, the table
  // remains in the document flow so the player list and live log move together.
  "&& > :last-child": {
    overflowX: "auto",
    overflowY: "visible",
    overscrollBehaviorX: "contain",
    WebkitOverflowScrolling: "touch",
    isolation: "isolate",
  },

  "& table": {
    borderLeft: 0,
    borderRight: 0,
    borderCollapse: "separate",
    borderSpacing: 0,
    boxSizing: "border-box",
  },

  // Keep a stable header height without creating a second vertical scroll
  // context. Horizontally sticky columns continue to come from table metadata.
  "& thead th": {
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
  },

  [theme.breakpoints.up("lg")]: {
    "--player-table-row-height": `${PLAYER_TABLE_LAYOUT.desktopRowHeight}px`,

    "& tbody td:not([colspan]) .MuiIconButton-root, & tbody td:not([colspan]) .MuiCheckbox-root":
      {
        minWidth: 32,
        minHeight: 32,
      },
  },
}));

export default PlayerTableLayout;
