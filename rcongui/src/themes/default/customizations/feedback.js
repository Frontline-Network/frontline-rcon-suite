import { alpha } from '@mui/material/styles';
import { FRONTLINE_GEOMETRY } from '../../foundation.mjs';

/* eslint-disable import/prefer-default-export */
export const feedbackCustomizations = ({ orange, gray }) => ({
  MuiAlert: {
    styleOverrides: {
      root: ({ theme, ownerState }) => ({
        borderRadius: FRONTLINE_GEOMETRY.radius.control,
        ...(ownerState.severity === 'warning' && {
          backgroundColor: orange[100],
          color: theme.palette.text.primary,
          border: `1px solid ${alpha(orange[300], 0.5)}`,
          '& .MuiAlert-icon': {
            color: orange[500],
          },
          ...theme.applyStyles('dark', {
            backgroundColor: `${alpha(orange[900], 0.5)}`,
            border: `1px solid ${alpha(orange[800], 0.5)}`,
          }),
        }),
      }),
    },
  },
  MuiDialog: {
    styleOverrides: {
      root: ({ theme }) => ({
        '& .MuiDialog-paper': {
          borderRadius: FRONTLINE_GEOMETRY.radius.overlay,
          border: '1px solid',
          borderColor: theme.palette.divider,
        },
      }),
    },
  },
  MuiLinearProgress: {
    styleOverrides: {
      root: ({ theme }) => ({
        height: 8,
        borderRadius: theme.shape.borderRadius,
        backgroundColor: gray[200],
        ...theme.applyStyles('dark', {
          backgroundColor: gray[800],
        }),
      }),
    },
  },
});
