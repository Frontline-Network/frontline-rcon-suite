import {
  Divider,
  Drawer,
  IconButton,
  Stack,
  styled,
  ToggleButton,
  ToggleButtonGroup,
  Toolbar,
  Typography,
} from "@mui/material";
import { useEffect, useState } from "react";
import CloseIcon from "@mui/icons-material/Close";
import { useTranslation } from "react-i18next";

const ResponsiveDrawer = styled(Drawer)(({ theme }) => ({
  zIndex: theme.zIndex.modal,
  "& .MuiDrawer-paper": {
    width: "100%",
    [theme.breakpoints.up("sm")]: {
      width: "20rem",
    },
  },
}));

const Wrapper = styled(Stack)(({ theme }) => ({
  width: "100%",
  height: "100%",
  overflowX: "hidden",
  paddingTop: theme.spacing(1),
  paddingBottom: theme.spacing(2),
  paddingLeft: theme.spacing(2),
  paddingRight: theme.spacing(2),
  gap: theme.spacing(2),
  [theme.breakpoints.up("sm")]: {
    width: "20rem",
  },
}));

const TableConfigDrawer = ({
  name,
  open,
  onClose,
  config,
  children,
}) => {
  const { t } = useTranslation();
  const [pendingConfig, setPendingConfig] = useState(null);

  const handleTableFontSizeChange = (e, fontSize) => {
    if (fontSize === null) return;
    setPendingConfig((prev) => ({ ...prev, fontSize }));
  };

  const handleTableDensityChange = (e, density) => {
    if (density === null) return;
    setPendingConfig((prev) => ({ ...prev, density }));
  };

  const handleClose = () => {
    onClose(pendingConfig);
  };

  useEffect(() => {
    setPendingConfig({ ...config });
  }, [open]);

  return (
    <ResponsiveDrawer open={open} onClose={handleClose}>
      <Toolbar
        disableGutters
        sx={{
          justifyContent: "space-between",
          px: 2,
        }}
      >
        <Typography sx={{ fontWeight: 500 }}>
          {t("tableConfig.title", { name: name || t("tableConfig.defaultName") })}
        </Typography>
        <IconButton onClick={handleClose}>
          <CloseIcon />
        </IconButton>
      </Toolbar>
      <Divider />

      {pendingConfig && (
        <Wrapper>
          <div>
            <Typography
              sx={{
                mb: 1,
                fontSize: "0.85rem",
                textTransform: "uppercase",
                letterSpacing: 1.5,
              }}
            >
              {t("tableConfig.fontSize")}
            </Typography>
            <ToggleButtonGroup
              value={pendingConfig.fontSize}
              exclusive
              onChange={handleTableFontSizeChange}
              aria-label={t("tableConfig.fontSize")}
              fullWidth
            >
              <ToggleButton value="small" aria-label={t("tableConfig.small")}>
                {t("tableConfig.small")}
              </ToggleButton>
              <ToggleButton value="normal" aria-label={t("tableConfig.normal")}>
                {t("tableConfig.normal")}
              </ToggleButton>
              <ToggleButton value="large" aria-label={t("tableConfig.large")}>
                {t("tableConfig.large")}
              </ToggleButton>
            </ToggleButtonGroup>
          </div>
          <div>
            <Typography
              sx={{
                mb: 1,
                fontSize: "0.85rem",
                textTransform: "uppercase",
                letterSpacing: 1.5,
              }}
            >
              {t("tableConfig.density")}
            </Typography>
            <ToggleButtonGroup
              value={pendingConfig.density}
              exclusive
              onChange={handleTableDensityChange}
              aria-label={t("tableConfig.density")}
              fullWidth
            >
              <ToggleButton value="dense" aria-label={t("tableConfig.dense")}>
                {t("tableConfig.dense")}
              </ToggleButton>
              <ToggleButton value="normal" aria-label={t("tableConfig.normal")}>
                {t("tableConfig.normal")}
              </ToggleButton>
              <ToggleButton value="comfortable" aria-label={t("tableConfig.comfortable")}>
                {t("tableConfig.comfortable")}
              </ToggleButton>
            </ToggleButtonGroup>
          </div>
          {children}
        </Wrapper>
      )}
    </ResponsiveDrawer>
  );
};

export default TableConfigDrawer;
