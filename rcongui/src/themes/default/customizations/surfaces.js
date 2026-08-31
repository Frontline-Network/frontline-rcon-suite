/* eslint-disable import/prefer-default-export */
export const surfacesCustomizations = () => ({
  MuiAccordion: {
    defaultProps: {
      elevation: 0,
      disableGutters: true,
    },
    styleOverrides: {
      root: ({ theme }) => ({
        padding: 4,
        overflow: 'clip',
        backgroundColor: theme.palette.background.default,
        border: '1px solid',
        borderColor: theme.palette.divider,
        ':before': {
          backgroundColor: 'transparent',
        },
        '&:not(:last-of-type)': {
          borderBottom: 'none',
        },
        '&:first-of-type': {
          borderTopLeftRadius: theme.shape.borderRadius,
          borderTopRightRadius: theme.shape.borderRadius,
        },
        '&:last-of-type': {
          borderBottomLeftRadius: theme.shape.borderRadius,
          borderBottomRightRadius: theme.shape.borderRadius,
        },
      }),
    },
  },
  MuiAccordionSummary: {
    styleOverrides: {
      root: ({ theme }) => ({
        border: 'none',
        borderRadius: theme.shape.borderRadius,
        '&:hover': { backgroundColor: theme.palette.action.hover },
        '&:focus-visible': { backgroundColor: 'transparent' },
      }),
    },
  },
  MuiAccordionDetails: {
    styleOverrides: {
      root: { mb: 20, border: 'none' },
    },
  },
  MuiPaper: {
    defaultProps: {
      elevation: 0,
    },
  },
  MuiCard: {
    styleOverrides: {
      root: ({ theme }) => {
        return {
          padding: 14,
          gap: 14,
          transition: 'all 100ms ease',
          backgroundColor: theme.palette.background.paper,
          borderRadius: theme.shape.borderRadius,
          border: `1px solid ${theme.palette.divider}`,
          boxShadow: 'none',
          variants: [
            {
              props: {
                variant: 'outlined',
              },
              style: {
                border: `1px solid ${theme.palette.divider}`,
                boxShadow: 'none',
                background: theme.palette.background.paper,
              },
            },
          ],
        };
      },
    },
  },
  MuiCardContent: {
    styleOverrides: {
      root: {
        padding: 0,
        '&:last-child': { paddingBottom: 0 },
      },
    },
  },
  MuiCardHeader: {
    styleOverrides: {
      root: ({ theme }) => ({
        padding: 0,
        paddingBottom: 10,
        marginBottom: 10,
        borderBottom: `1px solid ${theme.palette.divider}`,
        '& .MuiCardHeader-title': {
          color: theme.palette.primary.light,
        },
      }),
    },
  },
  MuiCardActions: {
    styleOverrides: {
      root: {
        padding: 0,
      },
    },
  },
});
