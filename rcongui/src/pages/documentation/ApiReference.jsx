import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Chip,
  Divider,
  LinearProgress,
  List,
  ListItemButton,
  MenuItem,
  Pagination,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import SectionSurface from "@/components/shared/SectionSurface";
import { cmd } from "@/utils/fetchUtils";
import { apiGuide } from "./content";
import DocumentationText from "./DocumentationText";
import {
  filterApiDocumentation,
  localizeApiDocumentation,
  normalizeApiDocumentation,
  apiEndpointPath,
} from "./api-reference.mjs";

const PAGE_SIZE = 12;
const mono = { fontFamily: "monospace", overflowWrap: "anywhere" };

function EndpointDetails({ item, t }) {
  return (
    <Box
      component="article"
      aria-labelledby="api-endpoint-title"
      sx={{ p: { xs: 2, md: 3 }, minWidth: 0 }}
    >
      <Stack
        direction="row"
        useFlexGap
        flexWrap="wrap"
        gap={0.75}
        sx={{ mb: 1.5 }}
      >
        {item.methods.map((method) => (
          <Chip size="small" variant="outlined" key={method} label={method} />
        ))}
      </Stack>
      <Typography id="api-endpoint-title" component="h2" variant="h6" sx={mono}>
        {item.endpoint}
      </Typography>
      <Typography
        component="p"
        color="text.secondary"
        sx={{ ...mono, fontSize: "0.8rem", mt: 1, mb: 3 }}
      >
        {apiEndpointPath(item)}
      </Typography>
      <Typography component="h3" variant="subtitle1" sx={{ mb: 1 }}>
        {t("documentation.description")}
      </Typography>
      <Typography
        sx={{
          whiteSpace: "pre-wrap",
          overflowWrap: "anywhere",
          color: "text.secondary",
          fontSize: "0.875rem",
          lineHeight: 1.75,
        }}
      >
        {item.description || t("documentation.noDescription")}
      </Typography>
      {item.technicalDescription && (
        <Box
          component="details"
          key={item.endpoint}
          sx={{
            mt: 2,
            fontSize: "0.8125rem",
            color: "text.secondary",
            "& summary": {
              cursor: "pointer",
              py: 1,
              color: "text.primary",
              "&:focus-visible": {
                outline: "2px solid",
                outlineColor: "primary.main",
              },
            },
          }}
        >
          <Box component="summary">
            {t("documentation.technicalDescription")}
          </Box>
          <Typography
            component="div"
            sx={{
              whiteSpace: "pre-wrap",
              overflowWrap: "anywhere",
              fontSize: "inherit",
              lineHeight: 1.75,
              mt: 1,
            }}
          >
            {item.technicalDescription}
          </Typography>
        </Box>
      )}
      <Divider sx={{ my: 3 }} />
      <Typography component="h3" variant="subtitle1" sx={{ mb: 1 }}>
        {t("documentation.permissions")}
      </Typography>
      {item.permissions.length ? (
        <>
          <Typography color="text.secondary" variant="body2">
            {t("documentation.allPermissions")}
          </Typography>
          <Box
            component="ul"
            sx={{ pl: 2.5, "& li": { ...mono, fontSize: "0.8rem", my: 1 } }}
          >
            {item.permissions.map((permission) => (
              <li key={permission}>{permission}</li>
            ))}
          </Box>
        </>
      ) : (
        <Typography color="text.secondary" variant="body2">
          {t("documentation.noPermissions")}
        </Typography>
      )}
      <Button
        component={Link}
        to="/documentation?topic=roles"
        size="small"
        sx={{ mt: 1 }}
      >
        {t("documentation.rolesHelp")}
      </Button>
      <Divider sx={{ my: 3 }} />
      <Typography component="h3" variant="subtitle1" sx={{ mb: 1 }}>
        {t("documentation.arguments")}
      </Typography>
      {item.arguments.length > 0 && (
        <Box component="dl" sx={{ m: 0, mb: 2 }}>
          {item.arguments.map((arg) => (
            <Box
              key={arg.name}
              sx={{ py: 1.5, borderBottom: 1, borderColor: "divider" }}
            >
              <Typography
                component="dt"
                sx={{ ...mono, fontSize: "0.875rem", fontWeight: 700 }}
              >
                {arg.name}
              </Typography>
              <Box component="dd" sx={{ ml: 0, mt: 0.5 }}>
                <Typography variant="body2" color="text.secondary" sx={mono}>
                  {arg.type || t("documentation.unspecified")}
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mt: 0.5, overflowWrap: "anywhere" }}
                >
                  {arg.default === null
                    ? t("documentation.noDefault")
                    : `${t("documentation.default")}: ${arg.default}`}
                </Typography>
              </Box>
            </Box>
          ))}
        </Box>
      )}
      <Typography color="text.secondary" variant="body2">
        {t("documentation.argumentsLimit")}
      </Typography>
      <Typography component="h3" variant="subtitle1" sx={{ mt: 3, mb: 1 }}>
        {t("documentation.returnType")}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={mono}>
        {item.returnType || t("documentation.unspecified")}
      </Typography>
    </Box>
  );
}

export default function ApiReference({ language }) {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const search = params.get("q") || "";
  const method = params.get("method") || "";
  const [page, setPage] = useState(1);
  const query = useQuery({
    queryKey: ["api-documentation"],
    queryFn: async () =>
      normalizeApiDocumentation(
        await cmd.GET_API_DOCUMENTATION({ throwRouteError: false })
      ),
    staleTime: 5 * 60 * 1000,
    retry: false,
    refetchOnWindowFocus: false,
  });
  const entries = useMemo(
    () => localizeApiDocumentation(query.data || [], language),
    [query.data, language]
  );
  const filtered = useMemo(
    () => filterApiDocumentation(entries, search, method),
    [entries, search, method]
  );
  const requested = params.get("endpoint");
  useEffect(() => {
    const index = filtered.findIndex((item) => item.endpoint === requested);
    setPage(index < 0 ? 1 : Math.floor(index / PAGE_SIZE) + 1);
  }, [requested, filtered]);
  const selected =
    filtered.find((item) => item.endpoint === requested) || filtered[0];
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, pages);
  const visible = filtered.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  );
  const methods = [...new Set(entries.flatMap((item) => item.methods))].sort();
  const selectEndpoint = (endpoint) => {
    const next = new URLSearchParams(params);
    next.set("endpoint", endpoint);
    setParams(next, { preventScrollReset: true });
  };
  const updateFilters = (nextSearch, nextMethod) => {
    const next = new URLSearchParams({ tab: "api" });
    if (nextSearch) next.set("q", nextSearch);
    if (nextMethod) next.set("method", nextMethod);
    setParams(next, { replace: true, preventScrollReset: true });
    setPage(1);
  };
  return (
    <Stack gap={2}>
      <Accordion
        disableGutters
        elevation={0}
        slotProps={{ heading: { component: "h2" } }}
        sx={{
          border: 1,
          borderColor: "divider",
          "&:before": { display: "none" },
        }}
      >
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          aria-controls="api-guide-content"
          id="api-guide-heading"
        >
          <Box>
            <Typography component="span" variant="subtitle1">
              {t("documentation.apiGuide")}
            </Typography>
            <Typography
              component="span"
              display="block"
              variant="body2"
              color="text.secondary"
            >
              {t("documentation.apiGuideSummary")}
            </Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails id="api-guide-content" sx={{ p: { xs: 2, md: 3 } }}>
          <DocumentationText>{apiGuide[language]}</DocumentationText>
        </AccordionDetails>
      </Accordion>
      {import.meta.env.MODE === "fake" && (
        <Alert severity="info">{t("documentation.preview")}</Alert>
      )}
      {import.meta.env.MODE !== "fake" && (
        <Typography variant="body2" color="text.secondary">
          {t("documentation.source")}
        </Typography>
      )}
      {query.isPending && (
        <LinearProgress aria-label={t("documentation.loading")} />
      )}
      {query.isError && (
        <Alert
          severity="error"
          action={
            <Button
              color="inherit"
              disabled={query.isFetching}
              onClick={() => query.refetch()}
            >
              {t("documentation.retry")}
            </Button>
          }
        >
          {t("documentation.loadError")}
        </Alert>
      )}
      {!query.isPending && !query.isError && (
        <>
          <Stack direction={{ xs: "column", sm: "row" }} gap={2}>
            <TextField
              fullWidth
              label={t("documentation.searchApi")}
              value={search}
              onChange={(event) => {
                updateFilters(event.target.value, method);
              }}
            />
            <TextField
              select
              label={t("documentation.method")}
              value={method || "all"}
              onChange={(event) => {
                updateFilters(
                  search,
                  event.target.value === "all" ? "" : event.target.value
                );
              }}
              sx={{ width: { xs: "100%", sm: 180 }, flexShrink: 0 }}
            >
              <MenuItem value="all">{t("documentation.allMethods")}</MenuItem>
              {methods.map((value) => (
                <MenuItem key={value} value={value}>
                  {value}
                </MenuItem>
              ))}
            </TextField>
          </Stack>
          <Typography role="status" variant="body2" color="text.secondary">
            {t("documentation.results", {
              count: filtered.length,
              total: entries.length,
            })}
          </Typography>
          {requested &&
            !entries.some((item) => item.endpoint === requested) && (
              <Alert severity="info">
                {t("documentation.endpointMissing")}
              </Alert>
            )}
          {filtered.length === 0 ? (
            <SectionSurface sx={{ p: 3 }}>
              <Typography>
                {t(
                  entries.length
                    ? "documentation.noResults"
                    : "documentation.emptyApi"
                )}
              </Typography>
              {(search || method) && (
                <Button
                  sx={{ mt: 1 }}
                  onClick={() => {
                    updateFilters("", "");
                  }}
                >
                  {t("documentation.clear")}
                </Button>
              )}
            </SectionSurface>
          ) : (
            <SectionSurface
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "minmax(0, 1fr)",
                  lg: "minmax(260px, 0.85fr) minmax(0, 1.65fr)",
                },
                alignItems: "start",
              }}
            >
              <Box
                sx={{
                  minWidth: 0,
                  borderRight: { lg: 1 },
                  borderBottom: { xs: 1, lg: 0 },
                  borderColor: { xs: "divider", lg: "divider" },
                }}
              >
                <Box sx={{ display: { xs: "block", lg: "none" }, p: 2 }}>
                  <TextField
                    fullWidth
                    select
                    label={t("documentation.endpoint")}
                    value={selected?.endpoint || ""}
                    onChange={(event) => selectEndpoint(event.target.value)}
                    SelectProps={{
                      MenuProps: {
                        PaperProps: {
                          sx: { maxHeight: 360, maxWidth: "90vw" },
                        },
                      },
                    }}
                  >
                    {filtered.map((item) => (
                      <MenuItem
                        key={item.endpoint}
                        value={item.endpoint}
                        sx={{
                          ...mono,
                          fontSize: "0.8rem",
                          whiteSpace: "normal",
                        }}
                      >
                        {item.endpoint}
                      </MenuItem>
                    ))}
                  </TextField>
                </Box>
                <Box sx={{ display: { xs: "none", lg: "block" } }}>
                  <List
                    component="nav"
                    aria-label={t("documentation.endpoints")}
                    disablePadding
                    sx={{ py: 1 }}
                  >
                    {visible.map((item) => (
                      <ListItemButton
                        key={item.endpoint}
                        selected={selected?.endpoint === item.endpoint}
                        aria-current={
                          selected?.endpoint === item.endpoint
                            ? "true"
                            : undefined
                        }
                        onClick={() => selectEndpoint(item.endpoint)}
                        sx={{
                          alignItems: "flex-start",
                          flexDirection: "column",
                          px: 2,
                          py: 1.25,
                          borderRadius: "0 !important",
                        }}
                      >
                        <Typography variant="caption" color="text.secondary">
                          {item.methods.join(" · ")}
                        </Typography>
                        <Typography
                          sx={{ ...mono, fontSize: "0.8rem", maxWidth: "100%" }}
                        >
                          {item.endpoint}
                        </Typography>
                      </ListItemButton>
                    ))}
                  </List>
                  <Pagination
                    aria-label={t("documentation.pagination")}
                    getItemAriaLabel={(type, number) =>
                      type === "page"
                        ? t("documentation.page", { page: number })
                        : t(
                            type === "previous"
                              ? "documentation.previous"
                              : "documentation.next"
                          )
                    }
                    count={pages}
                    page={currentPage}
                    size="small"
                    siblingCount={0}
                    onChange={(_event, value) => {
                      setPage(value);
                      selectEndpoint(
                        filtered[(value - 1) * PAGE_SIZE].endpoint
                      );
                    }}
                    sx={{ p: 1.5, borderTop: 1, borderColor: "divider" }}
                  />
                </Box>
              </Box>
              {selected && <EndpointDetails item={selected} t={t} />}
            </SectionSurface>
          )}
        </>
      )}
    </Stack>
  );
}
