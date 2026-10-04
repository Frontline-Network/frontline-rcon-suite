import {
  AssessmentOutlined,
  GroupsRounded,
  TableChartOutlined,
} from "@mui/icons-material";
import {
  Box,
  ButtonBase,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import PageHeader from "@/components/shared/PageHeader";

export const LiveCommandBar = ({
  layoutMode,
  onLayoutModeChange,
  splitDisabled,
  settingsControl,
}) => {
  const { t } = useTranslation();
  const theme = useTheme();
  const isWardogs = theme.frontline?.appearance?.preset === "wardogs";
  const isCompact = useMediaQuery(theme.breakpoints.down("md"));

  return (
    <Box data-theme-surface="panel"
      component="section"
      aria-labelledby="live-operations-title"
      sx={(theme) => ({
        border: isWardogs ? 0 : `1px solid ${theme.palette.divider}`,
        bgcolor: isWardogs ? "transparent" : "background.paper",
        mb: isWardogs ? 3 : 1,
      })}
    >
      {isWardogs ? (
        <PageHeader
          titleId="live-operations-title"
          title={t("views.live.title")}
          subtitle={t("views.live.subtitle")}
          actions={settingsControl}
        />
      ) : (
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderBottom: "1px solid",
            borderColor: "divider",
          }}
        >
          <Typography
            id="live-operations-title"
            component="h1"
            variant="subtitle1"
            sx={{
              minWidth: 0,
              color: "text.primary",
              fontFamily: '"Bahnschrift Condensed", "Arial Narrow", sans-serif',
              fontWeight: 800,
              letterSpacing: "0.08em",
              lineHeight: 1,
              m: 0,
              px: 1.5,
              py: 1,
              textTransform: "uppercase",
            }}
          >
            {t("views.live.title")}
          </Typography>
          {settingsControl}
        </Box>
      )}
      {isCompact ? (
        <Box
          role="tablist"
          aria-label={t("views.live.layout")}
          sx={{
            display: "grid",
            gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
          }}
        >
          <ButtonBase
            role="tab"
            aria-selected={layoutMode !== "logs"}
            onClick={() => onLayoutModeChange("players")}
            sx={(theme) => ({
              gap: 0.75,
              minHeight: 48,
              px: 0.5,
              ...(layoutMode !== "logs" && {
                color: "primary.light",
                boxShadow: `inset 0 -2px 0 ${theme.palette.primary.main}`,
              }),
              "&.Mui-focusVisible": {
                outline: `2px solid ${theme.palette.primary.main}`,
                outlineOffset: -3,
              },
            })}
          >
            <GroupsRounded sx={{ fontSize: "1rem" }} />
            <Typography variant="button">
              {t("views.live.mobileOperationsTab", { defaultValue: "Einsatz" })}
            </Typography>
          </ButtonBase>
          <ButtonBase
            role="tab"
            aria-selected={layoutMode === "logs"}
            onClick={() => onLayoutModeChange("logs")}
            sx={(theme) => ({
              gap: 0.75,
              minHeight: 48,
              px: 0.5,
              ...(layoutMode === "logs" && {
                color: "primary.light",
                boxShadow: `inset 0 -2px 0 ${theme.palette.primary.main}`,
              }),
              "&.Mui-focusVisible": {
                outline: `2px solid ${theme.palette.primary.main}`,
                outlineOffset: -3,
              },
            })}
          >
            <AssessmentOutlined sx={{ fontSize: "1rem" }} />
            <Typography variant="button">
              {t("views.live.mobileLogTab", { defaultValue: "Protokoll" })}
            </Typography>
          </ButtonBase>
        </Box>
      ) : (
        <ToggleButtonGroup
          value={layoutMode}
          exclusive
          onChange={(_, value) => value && onLayoutModeChange(value)}
          aria-label={t("views.live.layout")}
          size="small"
          sx={(theme) => ({
            display: "flex",
            px: 1,
            py: 0.75,
            "& .MuiToggleButton-root": {
              border: 0,
              borderRadius: 0,
              gap: 0.75,
              minHeight: 36,
              px: { xs: 1.25, sm: 2.5 },
            },
            "& .Mui-selected": {
              boxShadow: `inset 0 -2px 0 ${theme.palette.primary.main}`,
            },
          })}
        >
          <ToggleButton
            value="split"
            disabled={splitDisabled}
            title={splitDisabled ? t("views.live.splitUnavailable") : undefined}
            aria-describedby={
              splitDisabled ? "live-split-unavailable" : undefined
            }
          >
            <GroupsRounded sx={{ fontSize: "1rem" }} />
            {t("views.live.splitView")}
          </ToggleButton>
          <ToggleButton value="players">
            <TableChartOutlined sx={{ fontSize: "1rem" }} />
            {t("views.live.players")}
          </ToggleButton>
          <ToggleButton value="logs">
            <AssessmentOutlined sx={{ fontSize: "1rem" }} />
            {t("views.live.logs")}
          </ToggleButton>
        </ToggleButtonGroup>
      )}
      {splitDisabled ? (
        <Typography
          id="live-split-unavailable"
          sx={{
            position: "absolute",
            width: "1px",
            height: "1px",
            p: 0,
            m: "-1px",
            overflow: "hidden",
            clip: "rect(0 0 0 0)",
            whiteSpace: "nowrap",
            border: 0,
          }}
        >
          {t("views.live.splitUnavailable")}
        </Typography>
      ) : null}
    </Box>
  );
};
