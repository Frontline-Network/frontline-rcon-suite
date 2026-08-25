import { cmd } from "@/utils/fetchUtils";
import {
  Form,
  useLoaderData,
  useNavigation,
  useSubmit,
} from "react-router-dom";
import {
  Autocomplete,
  Box,
  Button,
  Chip,
  Collapse,
  FormControl,
  InputLabel,
  LinearProgress,
  MenuItem,
  Select,
  Stack,
  TextField,
  IconButton,
  Divider,
  Typography,
  useMediaQuery,
} from "@mui/material";
import { useMemo, useState } from "react";
import dayjs from "dayjs";
import { getAuditLogsColumns } from "./columns";
import Table from "@/components/table/Table";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
} from "@tanstack/react-table";
import { AuditLogCard } from "@/components/shared/card/AuditLogCard";
import { TableToolbar } from "@/components/table/TableToolbar";
import NavPagination from "@/pages/stats/games/nav-pagination";
import { TablePageSizeSelect } from "@/components/table/TablePageSizeSelect";
import DownloadIcon from "@mui/icons-material/Download";
import TuneRoundedIcon from "@mui/icons-material/TuneRounded";
import KeyboardArrowDownRoundedIcon from "@mui/icons-material/KeyboardArrowDownRounded";
import ChevronRightRoundedIcon from "@mui/icons-material/ChevronRightRounded";
import downloadLogs from "./download";
import { useTranslation } from "react-i18next";
import PageHeader from "@/components/shared/PageHeader";
import { demoAuditData, isFakeMode } from "@/mirage/demo-data";

const readAuditArguments = (value) => {
  try {
    return JSON.parse(value ?? "{}");
  } catch {
    return {};
  }
};

const MobileAuditLogList = ({ rows, onSelect }) => {
  const { t } = useTranslation();

  if (!rows.length) {
    return (
      <Typography color="text.secondary" sx={{ py: 4, textAlign: "center" }}>
        {t("common.noResults")}
      </Typography>
    );
  }

  return (
    <Stack component="ol" sx={{ listStyle: "none", m: 0, p: 0 }}>
      {rows.map((row) => {
        const auditLog = row.original;
        const args = readAuditArguments(auditLog.command_arguments);
        const subject = args.player_name ?? args.description ?? args.map_name;
        return (
          <Box
            component="li"
            key={auditLog.id ?? `${auditLog.creation_time}-${auditLog.command}`}
            sx={(theme) => ({ borderBottom: `1px solid ${theme.palette.divider}` })}
          >
            <Button
              color="inherit"
              fullWidth
              onClick={() => onSelect(auditLog)}
              sx={{
                alignItems: "stretch",
                borderRadius: 0,
                justifyContent: "flex-start",
                minHeight: 72,
                px: 1.25,
                py: 1,
                textAlign: "left",
                textTransform: "none",
              }}
            >
              <Stack width="100%" gap={0.35}>
                <Stack direction="row" alignItems="center" justifyContent="space-between" gap={1}>
                  <Chip label={auditLog.command} size="small" variant="outlined" />
                  <Typography color="text.secondary" variant="caption">
                    {dayjs(auditLog.creation_time).format("lll")}
                  </Typography>
                </Stack>
                <Stack direction="row" alignItems="center" justifyContent="space-between" gap={1}>
                  <Box sx={{ minWidth: 0 }}>
                    <Typography variant="body2" fontWeight={700} noWrap>
                      {auditLog.username || t("common.unknown")}
                    </Typography>
                    {subject ? (
                      <Typography color="text.secondary" variant="caption" noWrap>
                        {subject}
                      </Typography>
                    ) : null}
                  </Box>
                  <ChevronRightRoundedIcon color="action" aria-hidden />
                </Stack>
              </Stack>
            </Button>
          </Box>
        );
      })}
    </Stack>
  );
};

/**
 * @typedef {Object} AuditLogResponse
 * @property {AuditLog[]} audit_logs
 * @property {number} page
 * @property {number} page_size
 * @property {number} total_pages
 * @property {number} total_entries
 */

/**
 * @typedef {Object} AuditLogParams
 * @property {string} usernames
 * @property {string} commands
 * @property {string} parameters
 * @property {string} time_sort
 * @property {number} page
 * @property {number} page_size
 */

/**
 * @typedef {Object} AuditLoaderData
 * @property {AuditLog[]} auditLogs
 * @property {number} total_pages
 * @property {number} page
 * @property {AuditLogParams} fields
 */

/**
 * Helper function to get all values from a URL parameter
 *
 * If the parameter is provided without a value, it will be converted to an array with one empty string
 *
 * @param {string[]} value
 * @returns {string[]}
 */
const getAll = (value) => {
  if (Array.isArray(value) && value.length === 1 && value[0] === "") {
    return [];
  }
  return value;
};

/**
 * Loader for the audit logs page.
 *
 * Note: `usernames` and `commands` parameters can be included multiple times
 * which will be converted to an array of strings
 *
 * eg. `?usernames=John&usernames=Jane` will be converted to `["John", "Jane"]`
 *
 * @param {Request} request
 * @returns {Promise<AuditLoaderData>}
 */
export const loader = async ({ request }) => {
  const url = new URL(request.url);

  // Get all values from URL parameters and set defaults
  const usernames = getAll(url.searchParams.getAll("usernames"));
  const commands = getAll(url.searchParams.getAll("commands"));
  const parameters = url.searchParams.get("parameters") ?? "";
  const time_sort = url.searchParams.get("time_sort") ?? "desc";
  const page = url.searchParams.get("page") ?? 1;
  const page_size = url.searchParams.get("page_size") ?? 10;

  const fields = {
    usernames,
    commands,
    parameters,
    time_sort,
    page,
    page_size,
  };

  const params = new URLSearchParams();

  // Cannot use simple Object as some keys can be duplicated for multiple values
  // eg. `usernames` can have multiple values
  Object.entries(fields).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.forEach((v) => {
        if (v) params.append(key, v);
      });
    } else if (value !== "" && value !== null) {
      params.append(key, value);
    }
  });

  const auditLogsResult = isFakeMode() ? demoAuditData : await cmd.GET_AUDIT_LOGS({ params });
  const autocompleteOptions = isFakeMode()
    ? { usernames: ["Frontline Admin", "Leitstelle"], commands: ["message_player", "set_map"] }
    : await cmd.GET_AUDIT_LOGS_AUTOCOMPLETE();

  return {
    data: auditLogsResult,
    fields,
    autocompleteOptions,
  };
};

const AuditLogsPage = () => {
  const { t } = useTranslation();
  const { data, fields, autocompleteOptions } = useLoaderData();
  const compact = useMediaQuery((theme) => theme.breakpoints.down("md"));
  const auditLogsColumns = useMemo(() => getAuditLogsColumns(t), [t]);

  const { audit_logs, total_pages, page, page_size } = data;

  const submit = useSubmit();
  const navigation = useNavigation();

  const [formFields, setFormFields] = useState({
    usernames: fields.usernames,
    commands: fields.commands,
    parameters: fields.parameters,
    time_sort: fields.time_sort,
  });

  const [selectedAuditLog, setSelectedAuditLog] = useState(null);
  const hasActiveFilters = Boolean(
    fields.usernames.length || fields.commands.length || fields.parameters
  );
  const [filtersOpen, setFiltersOpen] = useState(hasActiveFilters);

  const table = useReactTable({
    data: audit_logs ?? [],
    columns: auditLogsColumns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    enableRowSelection: true,
    enableMultiRowSelection: false,
    onRowSelectionChange: (updater) => {
      // TODO:
      // This may cause a bug when paginating???
      const newSelection =
        typeof updater === "function" ? updater({}) : updater;
      const selectedId = Object.keys(newSelection)[0];
      const selectedLog = audit_logs[selectedId];
      setSelectedAuditLog(selectedLog);
    },
  });

  const handleInputChange = (e) => {
    const { name, value, checked } = e.target;
    setFormFields((prev) => ({
      ...prev,
      [name]: e.target.type === "checkbox" ? checked : value,
    }));
  };

  const getParams = (otherParams = {}) => {
    const params = new URLSearchParams();
    Object.entries({ ...formFields, ...otherParams }).forEach(
      ([key, value]) => {
        if (Array.isArray(value)) {
          value.forEach((v) => params.append(key, v));
        } else {
          params.append(key, value);
        }
      }
    );
    return params;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    submit(getParams(), { method: "GET" });
  };

  const handlePageSizeChange = (pageSize) => {
    submit(getParams({ page_size: pageSize }), {
      method: "GET",
      replace: true,
    });
  };

  const handleDownload = () => {
    downloadLogs(audit_logs);
  };

  return (
    <Stack direction={{ xs: "column" }} spacing={1} sx={{ mt: 2 }}>
      <PageHeader
        eyebrow={t("records.auditLogs.eyebrow")}
        title={t("records.auditLogs.title")}
        subtitle={t("records.auditLogs.subtitle")}
      />
      {compact ? (
        <Button
          aria-controls="audit-log-filters"
          aria-expanded={filtersOpen}
          onClick={() => setFiltersOpen((value) => !value)}
          startIcon={<TuneRoundedIcon />}
          endIcon={
            <KeyboardArrowDownRoundedIcon
              sx={{ transform: filtersOpen ? "rotate(180deg)" : "none" }}
            />
          }
          sx={{ justifyContent: "space-between", minHeight: 44 }}
          variant="outlined"
        >
          {t("records.auditLogs.filters")}
        </Button>
      ) : null}
      <Collapse in={!compact || filtersOpen}>
      <Form id="audit-log-filters" method="GET" onSubmit={handleSubmit}>
        <Stack spacing={2} direction={{ xs: "column", lg: "row" }}>
          <Autocomplete
            openText={t("common.openOptions")}
            closeText={t("common.closeOptions")}
            clearText={t("common.clearSelection")}
            noOptionsText={t("common.noResults")}
            multiple
            sx={{ width: { xs: "100%", lg: "25%" } }}
            clearOnEscape
            limitTags={2}
            id="usernames-autocomplete"
            options={autocompleteOptions.usernames}
            value={formFields.usernames}
            filterSelectedOptions
            onChange={(e, val) => {
              setFormFields((prev) => ({
                ...prev,
                usernames: val,
              }));
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                variant="outlined"
                label={t("records.auditLogs.user")}
                fullWidth
              />
            )}
          />
          <Autocomplete
            openText={t("common.openOptions")}
            closeText={t("common.closeOptions")}
            clearText={t("common.clearSelection")}
            noOptionsText={t("common.noResults")}
            multiple
            sx={{ width: { xs: "100%", lg: "25%" } }}
            clearOnEscape
            limitTags={2}
            id="commands-autocomplete"
            options={autocompleteOptions.commands}
            value={formFields.commands}
            filterSelectedOptions
            onChange={(e, val) => {
              setFormFields((prev) => ({
                ...prev,
                commands: val,
              }));
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                variant="outlined"
                name="commands"
                label={t("records.auditLogs.action")}
                fullWidth
              />
            )}
          />
          <TextField
            name="parameters"
            sx={{ width: { xs: "100%", lg: "25%" } }}
            value={formFields.parameters}
            onChange={handleInputChange}
            label={t("records.auditLogs.parameters")}
          />
          <FormControl sx={{ width: { xs: "100%", lg: "15%" } }}>
            <InputLabel id="time-sort-label">{t("records.auditLogs.sort")}</InputLabel>
            <Select
              labelId="time-sort-label"
              name="time_sort"
              value={formFields.time_sort}
              onChange={handleInputChange}
              label={t("records.auditLogs.sort")}
              fullWidth
            >
              <MenuItem value="desc">{t("records.auditLogs.newest")}</MenuItem>
              <MenuItem value="asc">{t("records.auditLogs.oldest")}</MenuItem>
            </Select>
          </FormControl>

          <Button
            type="submit"
            variant="contained"
            color="primary"
            sx={{ width: { xs: "100%", lg: "10%" } }}
            disabled={navigation.state === "loading"}
            onClick={handleSubmit}
          >
            {t("common.search")}
          </Button>
        </Stack>
      </Form>
      </Collapse>

      <Stack component="section" id="audit-logs-section" spacing={1} direction={{ xs: "column", lg: "row" }}>
        <Stack direction="column" sx={{ width: "100%", order: { xs: 2, lg: 1 } }}>
          <TableToolbar>
            <TablePageSizeSelect
              pageSize={page_size}
              setPageSize={handlePageSizeChange}
            />
            <Box sx={{ flexGrow: 1 }} />
            <NavPagination
              page={page}
              maxPages={total_pages}
              disabled={navigation.state === "loading"}
            />
            <Divider flexItem orientation="vertical" />
            <IconButton
              size="small"
              variant="contained"
              color="primary"
              sx={{
                "&.MuiIconButton-root": {
                  borderRadius: 0,
                },
              }}
              onClick={handleDownload}
              aria-label={t("records.auditLogs.download")}
              title={t("records.auditLogs.download")}
            >
              <DownloadIcon />
            </IconButton>
          </TableToolbar>
          {compact ? (
            <MobileAuditLogList
              rows={table.getRowModel().rows}
              onSelect={setSelectedAuditLog}
            />
          ) : (
            <Table
              table={table}
              columns={auditLogsColumns}
              rowProps={(row) => ({
                onClick: row.getToggleSelectedHandler(),
                sx: {
                  cursor: "pointer",
                  bgcolor: row.getIsSelected() ? "action.selected" : "inherit",
                  "&:hover": {
                    bgcolor: "action.hover",
                  },
                },
              })}
            />
          )}
        </Stack>
        {!compact || selectedAuditLog ? <Box
          sx={{
            order: { xs: 1, lg: 2 },
            maxWidth: 700,
            width: (theme) =>
              theme.breakpoints.down("lg") ? "100%" : "auto",
          }}
        >
          <AuditLogCard
            auditLog={selectedAuditLog}
            sx={{ position: "sticky", top: 0 }}
          />
        </Box> : null}
      </Stack>
    </Stack>
  );
};

export default AuditLogsPage;
