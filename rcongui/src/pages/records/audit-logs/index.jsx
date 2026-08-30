import { useEffect, useMemo, useState } from "react";
import {
  Box,
  Button,
  Drawer,
  LinearProgress,
  Stack,
  Typography,
  useMediaQuery,
} from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import { useLoaderData, useNavigation, useSubmit } from "react-router-dom";
import { useTranslation } from "react-i18next";
import dayjs from "dayjs";
import { cmd } from "@/utils/fetchUtils";
import PageHeader from "@/components/shared/PageHeader";
import NavPagination from "@/pages/stats/games/nav-pagination";
import { useGlobalStore } from "@/stores/global-state";
import { demoAuditData, isFakeMode } from "@/mirage/demo-data";
import downloadLogs from "./download";
import AuditLogsFilters from "./AuditLogsFilters";
import AuditLogsJournal from "./AuditLogsJournal";
import AuditLogInspector from "./AuditLogInspector";
import { getAuditCategoryCounts, getAuditEntryView } from "./audit-utils";

const getAll = (value) => {
  if (Array.isArray(value) && value.length === 1 && value[0] === "") {
    return [];
  }
  return value;
};

const filterDemoAuditLogs = (logs, fields) => {
  const parameters = String(fields.parameters || "").toLowerCase();
  const filtered = logs
    .filter(
      (entry) =>
        !fields.usernames.length || fields.usernames.includes(entry.username)
    )
    .filter(
      (entry) =>
        !fields.commands.length || fields.commands.includes(entry.command)
    )
    .filter((entry) =>
      !parameters
        ? true
        : `${entry.command_arguments || ""} ${entry.command_result || ""}`
            .toLowerCase()
            .includes(parameters)
    )
    .sort((a, b) => {
      const delta =
        dayjs(a.creation_time).valueOf() - dayjs(b.creation_time).valueOf();
      return fields.time_sort === "asc" ? delta : -delta;
    });

  const page = Number(fields.page) || 1;
  const pageSize = Number(fields.page_size) || 50;
  const start = (page - 1) * pageSize;

  return {
    audit_logs: filtered.slice(start, start + pageSize),
    total_pages: Math.ceil(filtered.length / pageSize),
    total_entries: filtered.length,
    page,
    page_size: pageSize,
  };
};

export const loader = async ({ request }) => {
  const url = new URL(request.url);
  const fields = {
    usernames: getAll(url.searchParams.getAll("usernames")),
    commands: getAll(url.searchParams.getAll("commands")),
    parameters: url.searchParams.get("parameters") ?? "",
    time_sort: url.searchParams.get("time_sort") ?? "desc",
    page: Number(url.searchParams.get("page") ?? 1),
    page_size: Number(url.searchParams.get("page_size") ?? 50),
  };

  const params = new URLSearchParams();
  Object.entries(fields).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.filter(Boolean).forEach((item) => params.append(key, item));
    } else if (value !== "" && value !== null) {
      params.append(key, String(value));
    }
  });

  const data = isFakeMode()
    ? filterDemoAuditLogs(demoAuditData.audit_logs, fields)
    : await cmd.GET_AUDIT_LOGS({ params });
  const autocompleteOptions = isFakeMode()
    ? {
        usernames: [
          ...new Set(demoAuditData.audit_logs.map((item) => item.username)),
        ],
        commands: [
          ...new Set(demoAuditData.audit_logs.map((item) => item.command)),
        ],
      }
    : await cmd.GET_AUDIT_LOGS_AUTOCOMPLETE();

  return { data, fields, autocompleteOptions };
};

export default function AuditLogsPage() {
  const { t } = useTranslation();
  const { data, fields, autocompleteOptions } = useLoaderData();
  const submit = useSubmit();
  const navigation = useNavigation();
  const compactInspector = useMediaQuery("(max-width: 1439px)");
  const server = useGlobalStore((state) => state.serverState);
  const [category, setCategory] = useState("all");
  const [status, setStatus] = useState("all");
  const [selectedKey, setSelectedKey] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const {
    audit_logs = [],
    total_pages = 0,
    total_entries = 0,
    page = 1,
    page_size = 50,
  } = data || {};

  const entries = useMemo(
    () => audit_logs.map((entry) => getAuditEntryView(entry, t)),
    [audit_logs, t]
  );
  const counts = useMemo(() => getAuditCategoryCounts(entries), [entries]);
  const visibleEntries = useMemo(
    () =>
      entries.filter(
        (entry) =>
          (category === "all" || entry.category === category) &&
          (status === "all" || entry.status === status)
      ),
    [category, entries, status]
  );
  const selectedEntry =
    visibleEntries.find((entry) => entry.key === selectedKey) || null;

  useEffect(() => {
    const selectionStillVisible = visibleEntries.some(
      (entry) => entry.key === selectedKey
    );
    if (selectionStillVisible) return;

    setDrawerOpen(false);
    setSelectedKey(compactInspector ? null : visibleEntries[0]?.key || null);
  }, [compactInspector, selectedKey, visibleEntries]);

  const handleSubmit = (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    formData.set("page", "1");
    [...formData.entries()].forEach(([key, value]) => {
      if (value === "") formData.delete(key);
    });
    submit(formData, { method: "GET", replace: true });
  };

  const handleReset = () => {
    setCategory("all");
    setStatus("all");
    submit(
      { time_sort: "desc", page_size: 50, page: 1 },
      { method: "GET", replace: true }
    );
  };

  const handleSelect = (entry) => {
    setSelectedKey(entry.key);
    if (compactInspector) setDrawerOpen(true);
  };

  const serverLabel =
    server?.short_name ||
    server?.name ||
    (server?.server_number
      ? t("records.auditLogs.serverNumber", { number: server.server_number })
      : null);
  const pageStart = total_entries
    ? (Number(page) - 1) * Number(page_size) + 1
    : 0;
  const pageEnd = Math.min(Number(page) * Number(page_size), total_entries);

  return (
    <Stack spacing={1} sx={{ mt: 0.5, width: "100%", minWidth: 0, pb: 2 }}>
      <PageHeader
        eyebrow={t("records.auditLogs.eyebrow")}
        title={t("records.auditLogs.title")}
        subtitle={t("records.auditLogs.subtitle")}
        actions={
          <Stack direction="row" alignItems="center" spacing={1.5}>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ whiteSpace: "nowrap" }}
            >
              {t("records.auditLogs.totalEntries", { count: total_entries })}
            </Typography>
            <Button
              variant="outlined"
              startIcon={<DownloadIcon />}
              onClick={() => downloadLogs(audit_logs)}
              disabled={!audit_logs.length}
              sx={{ borderRadius: 0, whiteSpace: "nowrap" }}
            >
              {t("records.auditLogs.exportPage")}
            </Button>
          </Stack>
        }
      />

      <AuditLogsFilters
        fields={fields}
        autocompleteOptions={autocompleteOptions}
        category={category}
        status={status}
        counts={counts}
        onCategoryChange={setCategory}
        onStatusChange={setStatus}
        onSubmit={handleSubmit}
        onReset={handleReset}
      />

      {navigation.state === "loading" && <LinearProgress />}

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: compactInspector
            ? "minmax(0, 1fr)"
            : "minmax(0, 1fr) 408px",
          gap: 1.25,
          alignItems: "start",
          minWidth: 0,
        }}
      >
        <Box sx={{ minWidth: 0 }}>
          <AuditLogsJournal
            entries={visibleEntries}
            selectedKey={selectedKey}
            onSelect={handleSelect}
          />
          <Stack
            direction={{ xs: "column", sm: "row" }}
            alignItems={{ xs: "stretch", sm: "center" }}
            gap={1}
            sx={{
              minHeight: 48,
              px: 1.25,
              py: 0.75,
              border: "1px solid",
              borderTop: 0,
              borderColor: "divider",
              bgcolor: "background.paper",
            }}
          >
            <Typography variant="caption" color="text.secondary">
              {t("records.auditLogs.loadedRange", {
                start: pageStart,
                end: pageEnd,
                total: total_entries,
                visible: visibleEntries.length,
              })}
            </Typography>
            <Box sx={{ flexGrow: 1 }} />
            <NavPagination
              page={Number(page)}
              maxPages={Number(total_pages)}
              disabled={navigation.state === "loading"}
            />
          </Stack>
        </Box>

        {!compactInspector && (
          <Box
            sx={{
              position: "sticky",
              top: 60,
              maxHeight: "calc(100vh - 76px)",
              overflowY: "auto",
              minWidth: 0,
            }}
          >
            <AuditLogInspector
              entry={selectedEntry}
              serverLabel={serverLabel}
              defaultRawOpen
            />
          </Box>
        )}
      </Box>

      <Drawer
        anchor="right"
        open={compactInspector && drawerOpen}
        onClose={() => setDrawerOpen(false)}
        PaperProps={{
          sx: {
            width: { xs: "100%", sm: 440 },
            maxWidth: "100vw",
            bgcolor: "background.default",
            p: { xs: 1, sm: 1.5 },
          },
        }}
      >
        <AuditLogInspector
          entry={selectedEntry}
          serverLabel={serverLabel}
          onClose={() => setDrawerOpen(false)}
        />
      </Drawer>
    </Stack>
  );
}
