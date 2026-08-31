import { useEffect, useMemo, useState } from "react";
import { useNavigate, useRevalidator } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Box,
  Button,
  ButtonBase,
  InputAdornment,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import RefreshIcon from "@mui/icons-material/Refresh";
import SearchIcon from "@mui/icons-material/Search";
import { useAuth } from "@/hooks/useAuth";
import { integrationGroups, integrationModules } from "./registry";
import { getIntegrationWorkbenchCopy } from "./workbench-copy";

const filterOptions = ["all", "discord", "commands", "hosting"];

const permissionSet = (permissions) =>
  new Set(
    (permissions?.permissions || []).map((entry) =>
      typeof entry === "string" ? entry : entry.permission
    )
  );

const getKnownStatus = (data) => {
  if (!data || typeof data !== "object") return "available";
  if (typeof data.enabled !== "boolean") return "configured";
  return data.enabled ? "active" : "inactive";
};

const statusIcon = {
  active: CheckCircleOutlineIcon,
  configured: CheckCircleOutlineIcon,
  inactive: ErrorOutlineIcon,
  available: HelpOutlineIcon,
};

const statusColor = {
  active: "success.main",
  configured: "success.main",
  inactive: "warning.main",
  available: "text.secondary",
};

export default function IntegrationsHub({
  activeCommand,
  activeData,
  children,
  isDirty,
}) {
  const { t, i18n } = useTranslation();
  const { permissions } = useAuth();
  const navigate = useNavigate();
  const revalidator = useRevalidator();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [knownStatuses, setKnownStatuses] = useState({});
  const [lastUpdated, setLastUpdated] = useState(() => new Date());
  const granted = useMemo(() => permissionSet(permissions), [permissions]);
  const workbenchCopy = useMemo(
    () => getIntegrationWorkbenchCopy(i18n.resolvedLanguage),
    [i18n.resolvedLanguage]
  );

  const visibleModules = useMemo(
    () =>
      integrationModules.filter(
        (module) =>
          permissions?.is_superuser || granted.has(module.viewPermission)
      ),
    [granted, permissions?.is_superuser]
  );

  useEffect(() => {
    if (!activeCommand) return;
    setKnownStatuses((current) => ({
      ...current,
      [activeCommand]: getKnownStatus(activeData),
    }));
    setLastUpdated(new Date());
  }, [activeCommand, activeData]);

  const filteredModules = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase();
    return visibleModules.filter((module) => {
      const matchesFilter =
        filter === "all" ||
        module.kind === filter ||
        (filter === "discord" && module.group === "discord");
      const haystack = `${t(module.nameKey)} ${t(
        module.purposeKey
      )}`.toLocaleLowerCase();
      return (
        matchesFilter &&
        (!normalizedQuery || haystack.includes(normalizedQuery))
      );
    });
  }, [filter, query, t, visibleModules]);

  const openModule = (module) => {
    if (module.command === activeCommand) return;
    if (
      isDirty &&
      !window.confirm(t("settings.integrations.unsavedConfirmation"))
    ) {
      return;
    }
    navigate(`/settings/integrations/${module.slug}`);
  };

  const refresh = () => {
    revalidator.revalidate();
    setLastUpdated(new Date());
  };

  return (
    <Box
      data-testid="integrations-hub"
      sx={{
        width: "100%",
        maxWidth: 1460,
        mx: "auto",
        pb: { xs: 9, md: 3 },
        "& .MuiButton-root, & .MuiButtonBase-root, & .MuiOutlinedInput-root, & .MuiPaper-root, & .MuiAlert-root":
          {
            borderRadius: 0,
          },
      }}
    >
      <Box
        component="header"
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "minmax(0, 1fr) auto" },
          gap: 2,
          alignItems: "end",
          mb: 2.25,
        }}
      >
        <Box>
          <Typography
            variant="overline"
            color="primary.main"
            sx={{ display: "block", letterSpacing: "0.08em" }}
          >
            {t("settings.integrations.eyebrow")}
          </Typography>
          <Typography
            component="h1"
            variant="h4"
            sx={{ fontWeight: 850, letterSpacing: "-0.02em" }}
          >
            {t("settings.integrations.title")}
          </Typography>
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ mt: 0.5, maxWidth: 980, lineHeight: 1.55 }}
          >
            {t("settings.integrations.description")}
          </Typography>
        </Box>
        <Stack alignItems={{ xs: "stretch", md: "flex-end" }} spacing={0.75}>
          <Typography variant="caption" color="text.secondary">
            {t("settings.integrations.lastUpdated", {
              value: lastUpdated.toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              }),
            })}
          </Typography>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={refresh}
            disabled={revalidator.state === "loading"}
          >
            {t("settings.integrations.refresh")}
          </Button>
        </Stack>
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "minmax(280px, 1fr) auto" },
          gap: 1,
          mb: 2,
        }}
      >
        <TextField
          size="small"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={t("settings.integrations.searchPlaceholder")}
          inputProps={{ "aria-label": t("settings.integrations.searchLabel") }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
        />
        <Box
          role="group"
          aria-label={workbenchCopy.filterLabel}
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "repeat(2, minmax(0, 1fr))",
              sm: "repeat(4, minmax(0, 1fr))",
              md: "repeat(4, auto)",
            },
            gap: 0.75,
            minWidth: 0,
          }}
        >
          {filterOptions.map((value) => (
            <Button
              key={value}
              variant={filter === value ? "contained" : "outlined"}
              onClick={() => setFilter(value)}
              aria-pressed={filter === value}
              sx={{ minWidth: 0, width: "100%", px: { xs: 1, md: 2 } }}
            >
              {t(`settings.integrations.filters.${value}`)}
            </Button>
          ))}
        </Box>
      </Box>

      <Box
        aria-hidden
        sx={{
          display: { xs: "none", md: "grid" },
          gridTemplateColumns:
            "minmax(260px, 0.95fr) minmax(360px, 1.4fr) minmax(160px, 0.52fr) 36px",
          gap: 2,
          px: 1.5,
          pb: 0.9,
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        {["module", "purpose", "configuration", "action"].map((column) => (
          <Typography
            key={column}
            variant="overline"
            color="text.secondary"
            sx={{ letterSpacing: "0.08em" }}
          >
            {t(`settings.integrations.columns.${column}`)}
          </Typography>
        ))}
      </Box>

      <Stack spacing={2}>
        {integrationGroups.map((group) => {
          const modules = filteredModules.filter(
            (module) => module.group === group.id
          );
          if (!modules.length) return null;

          return (
            <Box key={group.id}>
              <Typography
                variant="overline"
                color="primary.main"
                sx={{
                  display: "block",
                  px: 1.5,
                  py: 0.7,
                  letterSpacing: "0.08em",
                }}
              >
                {t(group.labelKey, { count: modules.length })}
              </Typography>
              <Box sx={{ border: "1px solid", borderColor: "divider" }}>
                {modules.map((module, moduleIndex) => {
                  const active = module.command === activeCommand;
                  const status = knownStatuses[module.command] || "available";
                  const StatusIcon = statusIcon[status];
                  const ModuleIcon = module.icon;

                  return (
                    <Box
                      key={module.command}
                      sx={{
                        borderTop: moduleIndex === 0 ? 0 : "1px solid",
                        borderColor: "divider",
                      }}
                    >
                      <ButtonBase
                        component="button"
                        type="button"
                        data-testid={`integration-module-${module.slug}`}
                        aria-expanded={active}
                        onClick={() => openModule(module)}
                        sx={{
                          width: "100%",
                          display: "grid",
                          gridTemplateColumns: {
                            xs: "minmax(0, 1fr) auto",
                            md: "minmax(260px, 0.95fr) minmax(360px, 1.4fr) minmax(160px, 0.52fr) 36px",
                          },
                          gap: { xs: 1, md: 2 },
                          alignItems: "center",
                          minHeight: { xs: 74, md: 52 },
                          px: 1.5,
                          py: { xs: 1.1, md: 0.8 },
                          textAlign: "left",
                          borderLeft: "2px solid",
                          borderLeftColor: active
                            ? "primary.main"
                            : "transparent",
                          bgcolor: active
                            ? "action.selected"
                            : "background.paper",
                          color: "text.primary",
                          "&:hover": { bgcolor: "action.hover" },
                          "&.Mui-focusVisible": {
                            outline: "2px solid",
                            outlineColor: "primary.main",
                            outlineOffset: -2,
                          },
                        }}
                      >
                        <Stack
                          direction="row"
                          spacing={1.25}
                          alignItems="center"
                          minWidth={0}
                        >
                          <Box
                            sx={{
                              display: "grid",
                              placeItems: "center",
                              width: 34,
                              height: 34,
                              flex: "0 0 auto",
                              border: "1px solid",
                              borderColor: active ? "primary.main" : "divider",
                              color: active ? "primary.main" : "text.secondary",
                            }}
                          >
                            <ModuleIcon fontSize="small" />
                          </Box>
                          <Box minWidth={0}>
                            <Typography variant="body2" fontWeight={800} noWrap>
                              {t(module.nameKey)}
                            </Typography>
                            <Typography
                              variant="caption"
                              color="text.secondary"
                              sx={{
                                display: { xs: "block", md: "none" },
                                mt: 0.15,
                              }}
                            >
                              {t(module.purposeKey)}
                            </Typography>
                          </Box>
                        </Stack>
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{ display: { xs: "none", md: "block" } }}
                        >
                          {t(module.purposeKey)}
                        </Typography>
                        <Stack
                          direction="row"
                          spacing={0.75}
                          alignItems="center"
                          sx={{ justifySelf: { xs: "end", md: "start" } }}
                        >
                          <StatusIcon
                            sx={{ fontSize: 18, color: statusColor[status] }}
                          />
                          <Typography
                            variant="body2"
                            color={statusColor[status]}
                            noWrap
                          >
                            {t(`settings.integrations.status.${status}`)}
                          </Typography>
                        </Stack>
                        <ChevronRightIcon
                          aria-hidden
                          sx={{
                            display: { xs: "none", md: "block" },
                            transform: active ? "rotate(90deg)" : "none",
                            transition: "transform 140ms ease",
                            color: "text.secondary",
                          }}
                        />
                      </ButtonBase>
                      {active && (
                        <Box
                          data-testid="integration-inline-editor"
                          sx={{
                            px: { xs: 1, sm: 1.5, md: 2 },
                            py: { xs: 1.5, md: 2 },
                            borderTop: "1px solid",
                            borderLeft: "2px solid",
                            borderColor: "divider",
                            borderLeftColor: "primary.main",
                            bgcolor: "background.default",
                          }}
                        >
                          {children}
                        </Box>
                      )}
                    </Box>
                  );
                })}
              </Box>
            </Box>
          );
        })}
      </Stack>

      {filteredModules.length === 0 && (
        <Box
          sx={{
            border: "1px solid",
            borderColor: "divider",
            p: 3,
            textAlign: "center",
          }}
        >
          <Typography variant="h6">
            {t("settings.integrations.emptyTitle")}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {t("settings.integrations.emptyDescription")}
          </Typography>
        </Box>
      )}
    </Box>
  );
}
