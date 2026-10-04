import { alpha, createTheme } from "@mui/material/styles";
import "@fontsource/roboto/400.css";
import "@fontsource/roboto/500.css";
import "@fontsource/roboto/700.css";
import { geometry, gray, typography } from "./tokens";
import { legacySurfaces } from "./legacySurfaces";

const mui = createTheme();
const raised = (theme) =>
  theme.palette.mode === "dark" ? "#1a1a1e" : "#f7f7f9";
const outline = (theme) => `2px solid ${theme.palette.primary.main}`;
const border = (theme) => `1px solid ${theme.palette.divider}`;
const popup = ({ theme }) => ({
  backgroundColor: raised(theme),
  backgroundImage: "none",
  color: theme.palette.text.primary,
  border: border(theme),
  borderRadius: 10,
  boxShadow: theme.shadows[8],
});

// Independent component system. No Frontline customizations are merged into
// Wardogs; shared application behavior stays in the existing React components.
export default function getWardogsTheme(themeComponents) {
  return {
    cssVariables: {
      colorSchemeSelector: "data-mui-color-scheme",
      cssVarPrefix: "template",
    },
    defaultColorScheme: "dark",
    colorSchemes: {
      light: { palette: { grey: gray } },
      dark: { palette: { grey: gray } },
    },
    typography,
    shape: { borderRadius: geometry.radius.control },
    shadows: ["none", "0 2px 8px rgba(0,0,0,0.12)", ...mui.shadows.slice(2)],
    frontline: { geometry },
    components: {
      MuiCssBaseline: { styleOverrides: (theme) => legacySurfaces(theme) },
      MuiButtonBase: {
        defaultProps: { disableRipple: true },
        styleOverrides: {
          root: ({ theme }) => ({
            "&:focus-visible": { outline: outline(theme), outlineOffset: 2 },
          }),
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: 6,
            minHeight: 36,
            padding: "6px 14px",
            boxShadow: "none",
            "&:hover": { boxShadow: "none" },
            "@media (pointer: coarse)": { minHeight: 44 },
          },
          containedPrimary: ({ theme }) => ({
            color: theme.palette.text.primary,
            backgroundColor:
              theme.palette.mode === "dark" ? "#2a282d" : "#e7e7eb",
            border: border(theme),
            "&:hover": {
              backgroundColor:
                theme.palette.mode === "dark" ? "#363239" : "#d9d7df",
              borderColor: theme.palette.primary.main,
            },
          }),
          outlined: ({ theme }) => ({
            borderColor: theme.palette.divider,
            "&:hover": {
              borderColor: theme.palette.primary.main,
              backgroundColor: theme.palette.action.hover,
            },
          }),
        },
      },
      MuiIconButton: {
        styleOverrides: {
          root: ({ theme }) => ({
            borderRadius: 6,
            color: theme.palette.text.secondary,
            "&:hover": {
              color: theme.palette.primary.main,
              backgroundColor: theme.palette.action.hover,
            },
            "@media (pointer: coarse)": { minWidth: 44, minHeight: 44 },
          }),
        },
      },
      MuiPaper: {
        defaultProps: { elevation: 0 },
        styleOverrides: {
          root: { backgroundImage: "none" },
          outlined: ({ theme }) => ({ borderColor: theme.palette.divider }),
        },
      },
      MuiCard: {
        styleOverrides: {
          root: ({ theme }) => ({
            backgroundColor: theme.palette.background.paper,
            border: border(theme),
            borderRadius: 10,
            padding: 18,
            gap: 16,
            boxShadow: "none",
          }),
        },
      },
      MuiCardHeader: {
        styleOverrides: {
          root: ({ theme }) => ({
            padding: "0 0 14px",
            marginBottom: 16,
            borderBottom: border(theme),
            "& .MuiCardHeader-title": {
              color: theme.palette.text.primary,
              fontSize: 14,
              fontWeight: 500,
            },
          }),
        },
      },
      MuiCardContent: {
        styleOverrides: {
          root: { padding: 0, "&:last-child": { paddingBottom: 0 } },
        },
      },
      MuiCardActions: {
        styleOverrides: { root: { padding: "12px 0 0", gap: 8 } },
      },
      MuiDrawer: {
        styleOverrides: {
          paper: ({ theme }) => ({
            backgroundColor: theme.palette.background.paper,
            backgroundImage: "none",
            borderColor: theme.palette.divider,
          }),
        },
      },
      MuiDialog: { styleOverrides: { paper: popup } },
      MuiDialogTitle: {
        styleOverrides: {
          root: ({ theme }) => ({
            padding: "20px 24px",
            borderBottom: border(theme),
            fontSize: 18,
            fontWeight: 500,
          }),
        },
      },
      MuiDialogContent: { styleOverrides: { root: { padding: 24 } } },
      MuiDialogActions: {
        styleOverrides: {
          root: ({ theme }) => ({
            padding: "16px 24px",
            gap: 8,
            borderTop: border(theme),
          }),
        },
      },
      MuiMenu: { styleOverrides: { paper: popup, list: { padding: 6 } } },
      MuiPopover: { styleOverrides: { paper: popup } },
      MuiMenuItem: {
        styleOverrides: {
          root: ({ theme }) => ({
            borderRadius: 6,
            padding: "9px 12px",
            minHeight: 36,
            gap: 10,
            "&.Mui-selected": {
              backgroundColor: theme.palette.action.selected,
              color: theme.palette.primary.light,
            },
          }),
        },
      },
      MuiList: { styleOverrides: { root: { padding: 8 } } },
      MuiListItemButton: { styleOverrides: { root: { borderRadius: 6 } } },
      MuiListItemIcon: {
        styleOverrides: {
          root: { minWidth: 32, color: "inherit", "& svg": { fontSize: 18 } },
        },
      },
      MuiListItemText: {
        styleOverrides: {
          root: { marginTop: 0, marginBottom: 0 },
          primary: { fontSize: 13, fontWeight: 400 },
          secondary: { fontSize: 12 },
        },
      },
      MuiListSubheader: {
        styleOverrides: {
          root: ({ theme }) => ({
            backgroundColor: "transparent",
            color: theme.palette.text.secondary,
            lineHeight: "32px",
            fontSize: 11,
          }),
        },
      },
      MuiOutlinedInput: {
        styleOverrides: {
          root: ({ theme }) => ({
            borderRadius: 6,
            backgroundColor: theme.palette.background.default,
            "& .MuiOutlinedInput-notchedOutline": {
              borderColor: theme.palette.divider,
            },
            "&:hover .MuiOutlinedInput-notchedOutline": {
              borderColor: theme.palette.text.disabled,
            },
            "&.Mui-focused": {
              boxShadow: `0 0 0 3px ${alpha(theme.palette.primary.main, 0.12)}`,
            },
            "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
              borderColor: theme.palette.primary.main,
              borderWidth: 1,
            },
          }),
          input: { padding: "10px 12px" },
        },
      },
      MuiFormLabel: {
        styleOverrides: {
          root: ({ theme }) => ({
            color: theme.palette.text.secondary,
            fontSize: 13,
            fontWeight: 500,
          }),
        },
      },
      MuiFormHelperText: {
        styleOverrides: { root: { marginLeft: 0, marginTop: 6 } },
      },
      MuiSelect: {
        styleOverrides: {
          select: { display: "flex", alignItems: "center" },
          icon: ({ theme }) => ({ color: theme.palette.text.secondary }),
        },
      },
      MuiCheckbox: {
        defaultProps: { size: "small" },
        styleOverrides: {
          root: ({ theme }) => ({ color: theme.palette.text.secondary }),
        },
      },
      MuiRadio: { defaultProps: { size: "small" } },
      MuiSwitch: { styleOverrides: { track: { borderRadius: 999 } } },
      MuiTabs: {
        styleOverrides: {
          root: ({ theme }) => ({ minHeight: 40, borderBottom: border(theme) }),
          indicator: { height: 2 },
        },
      },
      MuiTab: {
        styleOverrides: {
          root: ({ theme }) => ({
            minHeight: 40,
            minWidth: 0,
            padding: "10px 16px",
            textTransform: "none",
            fontWeight: 500,
            color: theme.palette.text.secondary,
          }),
        },
      },
      MuiToggleButton: {
        styleOverrides: {
          root: ({ theme }) => ({
            padding: "6px 12px",
            borderColor: theme.palette.divider,
            color: theme.palette.text.secondary,
            "&.Mui-selected": {
              backgroundColor: theme.palette.action.selected,
              color: theme.palette.primary.light,
            },
          }),
        },
      },
      MuiChip: {
        defaultProps: { size: "small" },
        styleOverrides: {
          root: ({ theme, ownerState }) => ({
            borderRadius: 6,
            height: 24,
            fontWeight: 500,
            ...(ownerState.color === "default" && {
              color: theme.palette.text.secondary,
              backgroundColor: raised(theme),
              border: border(theme),
            }),
          }),
          label: { paddingLeft: 8, paddingRight: 8 },
        },
      },
      MuiAlert: {
        styleOverrides: {
          root: ({ theme, ownerState }) => {
            const tone = theme.palette[ownerState.severity || "info"];
            return {
              borderRadius: 8,
              ...(ownerState.variant !== "filled" && {
                color: theme.palette.text.primary,
                backgroundColor: alpha(tone.main, 0.08),
                border: `1px solid ${alpha(tone.main, 0.28)}`,
                "& .MuiAlert-icon": { color: tone.main },
              }),
            };
          },
        },
      },
      MuiAccordion: {
        defaultProps: { disableGutters: true, elevation: 0 },
        styleOverrides: {
          root: ({ theme }) => ({
            backgroundColor: theme.palette.background.paper,
            border: border(theme),
            borderRadius: 8,
            "&::before": { display: "none" },
          }),
        },
      },
      MuiAccordionSummary: {
        styleOverrides: {
          root: { minHeight: 48 },
          content: { margin: "12px 0" },
        },
      },
      MuiDivider: {
        styleOverrides: {
          root: ({ theme }) => ({ borderColor: theme.palette.divider }),
        },
      },
      MuiLink: {
        defaultProps: { underline: "hover" },
        styleOverrides: { root: { textUnderlineOffset: 3 } },
      },
      MuiTooltip: {
        styleOverrides: {
          tooltip: ({ theme }) => ({
            backgroundColor: raised(theme),
            color: theme.palette.text.primary,
            border: border(theme),
            fontSize: 12,
            padding: "7px 10px",
            borderRadius: 6,
          }),
        },
      },
      MuiLinearProgress: {
        styleOverrides: {
          root: ({ theme }) => ({
            height: 5,
            borderRadius: 6,
            backgroundColor: theme.palette.action.hover,
          }),
        },
      },
      MuiTableContainer: {
        styleOverrides: {
          root: ({ theme }) => ({ border: border(theme), borderRadius: 10 }),
        },
      },
      MuiTableCell: {
        styleOverrides: {
          root: ({ theme }) => ({
            borderColor: theme.palette.divider,
            fontSize: 13,
          }),
          head: ({ theme }) => ({
            backgroundColor: raised(theme),
            color: theme.palette.text.secondary,
            fontWeight: 500,
          }),
        },
      },
      MuiTableRow: {
        styleOverrides: {
          root: ({ theme }) => ({
            "&.MuiTableRow-hover:hover": {
              backgroundColor: theme.palette.action.hover,
            },
          }),
        },
      },
      MuiDataGrid: {
        styleOverrides: {
          root: ({ theme }) => ({
            border: border(theme),
            borderRadius: 10,
            backgroundColor: theme.palette.background.paper,
            "--DataGrid-containerBackground": raised(theme),
            "& .MuiDataGrid-columnHeaders": {
              color: theme.palette.text.secondary,
              backgroundColor: raised(theme),
            },
            "& .MuiDataGrid-cell": { borderColor: theme.palette.divider },
            "& .MuiDataGrid-row:hover": {
              backgroundColor: theme.palette.action.hover,
            },
            "& .MuiDataGrid-row.Mui-selected": {
              backgroundColor: theme.palette.action.selected,
            },
          }),
        },
      },
      MuiPickersPopper: { styleOverrides: { paper: popup } },
      MuiChartsAxis: {
        styleOverrides: {
          root: ({ theme }) => ({
            "& .MuiChartsAxis-line, & .MuiChartsAxis-tick": {
              stroke: theme.palette.divider,
            },
            "& .MuiChartsAxis-tickLabel": {
              fill: theme.palette.text.secondary,
            },
          }),
        },
      },
      MuiChartsGrid: {
        styleOverrides: {
          root: ({ theme }) => ({
            "& line": {
              stroke: theme.palette.divider,
              strokeDasharray: "none",
            },
          }),
        },
      },
      MuiChartsTooltip: { styleOverrides: { table: popup } },
      ...themeComponents,
    },
  };
}
