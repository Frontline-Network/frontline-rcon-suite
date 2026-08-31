import { alpha } from "@mui/material/styles";
import { outlinedInputClasses } from "@mui/material/OutlinedInput";

import {
  FRONTLINE_GEOMETRY,
  frontlineFocusRing,
} from "../../foundation.mjs";

const focusOutline = (theme) =>
  frontlineFocusRing(alpha(theme.palette.primary.main, 0.72));

/* eslint-disable import/prefer-default-export */
export const foundationCustomizations = () => ({
  MuiButtonBase: {
    defaultProps: {
      disableRipple: true,
    },
    styleOverrides: {
      root: ({ theme }) => ({
        "&:focus-visible": {
          outline: focusOutline(theme),
          outlineOffset: FRONTLINE_GEOMETRY.focusRing.offset,
        },
      }),
    },
  },
  MuiOutlinedInput: {
    styleOverrides: {
      root: ({ theme }) => ({
        borderRadius: FRONTLINE_GEOMETRY.radius.control,
        transition: theme.transitions.create(
          ["border-color", "box-shadow", "background-color"],
          { duration: theme.transitions.duration.shortest }
        ),
        [`&.${outlinedInputClasses.focused}`]: {
          boxShadow: `0 0 0 ${FRONTLINE_GEOMETRY.focusRing.width}px ${alpha(
            theme.palette.primary.main,
            0.34
          )}`,
          [`& .MuiOutlinedInput-notchedOutline`]: {
            borderColor: theme.palette.primary.main,
          },
        },
      }),
    },
  },
  MuiFormLabel: {
    styleOverrides: {
      root: ({ theme }) => ({
        color: theme.palette.text.secondary,
        fontWeight: 700,
        "&.Mui-focused": {
          color: theme.palette.primary.light,
        },
      }),
    },
  },
  MuiFormHelperText: {
    styleOverrides: {
      root: {
        marginLeft: 0,
        marginRight: 0,
      },
    },
  },
});
