import { logActions } from "@/utils/lib";
import { Button, styled } from "@mui/material";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";

export function getVariantWidth(variant) {
  switch (variant) {
    case "icon":
      return "1.25em";
    case "short":
      return "4em";
    case "time":
      return "16ch";
    case "name":
      return "20ch";
    case "playerName":
      return "16ch";
    case "assignmentSummary":
      return "18ch";
    case "performanceSummary":
      return "15ch";
    case "statusSummary":
      return "10ch";
    case "fullname":
      return "30ch";
    case "action":
      return "24ch";
    case "content":
      return "auto";
    default:
      return "auto";
  }
}

export function getVariantMinWidth(variant) {
  switch (variant) {
    case "icon":
      return "1.25em";
    case "short":
      return "4em";
    case "time":
      return "16ch";
    case "name":
      return "20ch";
    case "playerName":
      return "16ch";
    case "assignmentSummary":
      return "18ch";
    case "performanceSummary":
      return "15ch";
    case "statusSummary":
      return "10ch";
    case "fullname":
      return "30ch";
    case "action":
      return "24ch";
    case "content":
      return "50ch";
    default:
      return "auto";
  }
}

export function getDensityPadding(density, theme) {
  switch (density) {
    case "dense":
      return {
        paddingRight: theme.spacing(0.5),
        paddingLeft: theme.spacing(0.5),
        paddingTop: theme.spacing(0.25),
        paddingBottom: theme.spacing(0.25),
      };
    case "comfortable":
      return {
        paddingRight: theme.spacing(1),
        paddingLeft: theme.spacing(1),
        paddingTop: theme.spacing(1),
        paddingBottom: theme.spacing(1),
      };
    default:
      return {
        paddingRight: theme.spacing(0.5),
        paddingLeft: theme.spacing(0.5),
        paddingTop: theme.spacing(0.5),
        paddingBottom: theme.spacing(0.5),
      };
  }
}

// The table will have a prop size ["small", "normal", "large"]
// Styles will be different based on the size property
// The property size won't be passed to the component, but rather it will be used in the styled component
export const StyledTable = styled("table", {
  shouldForwardProp: (prop) => prop !== "fontSize" || prop !== "density",
})((styledProps) => {
  const theme = styledProps.theme;
  const fontSize = styledProps.fontSize;
  const density = styledProps.density;

  return {
    // TABLE
    fontSize:
      fontSize === "small"
        ? "0.85rem"
        : fontSize === "large"
        ? "1.15rem"
        : "1rem",
    borderCollapse: "collapse",
    borderSpacing: 0,
    border: `1px solid ${theme.palette.divider}`,
    width: "100%",
    "& td": {
      ...getDensityPadding(density, theme),
      verticalAlign: "middle",
    },
    "& th": {
      ...getDensityPadding(density, theme),
      verticalAlign: "middle",
      height: "3rem",
    },
    "& tbody tr": {
      verticalAlign: "top",
    },
  };
});

export const StyledThead = styled("thead")(({ theme }) => ({
  backgroundColor: theme.palette.background.paper,
}));

export const StyledTh = styled("th", {
  shouldForwardProp: (prop) =>
    !["variant", "minWidth", "sticky", "stickyOffset"].includes(prop),
})((styledProps) => {
  const variant = styledProps.variant;
  const sticky = styledProps.sticky;
  return {
    width: getVariantWidth(variant),
    minWidth: getVariantMinWidth(variant),
    textAlign: variant === "icon" ? "center" : "left",
    paddingLeft: variant === "icon" ? 0 : undefined,
    paddingRight: variant === "icon" ? 0 : undefined,
    ...(sticky
      ? {
          position: "sticky",
          [sticky]: styledProps.stickyOffset ?? 0,
          zIndex: 4,
          backgroundColor: styledProps.theme.palette.background.paper,
        }
      : {}),
  };
});

export const StyledTd = styled("td", {
  shouldForwardProp: (prop) =>
    !["variant", "minWidth", "sticky", "stickyOffset"].includes(prop),
})((styledProps) => {
  const variant = styledProps.variant;
  const sticky = styledProps.sticky;

  return {
    width: getVariantWidth(variant),
    minWidth: getVariantMinWidth(variant),
    textAlign: variant === "icon" ? "center" : "left",
    ...(sticky
      ? {
          position: "sticky",
          [sticky]: styledProps.stickyOffset ?? 0,
          zIndex: 2,
          backgroundColor: styledProps.theme.palette.background.default,
        }
      : {}),
  };
});

export const StyledTr = styled("tr")(({ theme }) => ({
  borderBottom: `1px solid ${theme.palette.divider}`,
}));

export const Action = styled("div", {
  shouldForwardProp: (props) => props !== "type",
})(({ theme, type }) => ({
  "&::before": {
    content: `"${logActions[type] ?? logActions["UNKNOWN"]}"`,
    paddingRight: theme.spacing(1),
  },
  textAlign: "left",
}));

export const TextButton = styled((props) => (
  <span role="button" tabIndex={0} {...props} />
))(() => ({
  cursor: "pointer",
  width: "fit-content",
  "&:hover": {
    textDecoration: "underline",
  },
}));

export const HeaderButton = styled((props) => (
  <Button size="small" {...props} />
))(({ theme }) => ({
  width: "100%",
  borderRadius: 0,
  textAlign: "left",
  color: theme.palette.text.primary,
  fontSize: "1em",
  textDecoration: "none",
  textTransform: "none",
  minWidth: "fit-content",
}));

export const SortableHeader =
  (text, title) =>
  ({ column }) => {
    const isIconColumn = column.columnDef?.meta?.variant === "icon";

    return (
      <HeaderButton
        onClick={column.getToggleSortingHandler()}
        title={title || ""}
        sx={{ justifyContent: isIconColumn ? "center" : "flex-start" }}
      >
        {text}
        {column.getIsSorted() &&
          (column.getIsSorted() === "asc" ? (
            <ArrowUpwardIcon
              sx={{
                fontSize: "1em",
                width: "1em",
                height: "1em",
                ml: 0.5,
              }}
            />
          ) : (
            <ArrowDownwardIcon
              sx={{
                fontSize: "1em",
                width: "1em",
                height: "1em",
                ml: 0.5,
              }}
            />
          ))}
      </HeaderButton>
    );
  };
