import { useMemo, useState } from "react";
import { Box, Button, Stack, Typography } from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import { useLoaderData, useSubmit } from "react-router-dom";
import { useTranslation } from "react-i18next";
import dayjs from "dayjs";
import timezonePlugin from "dayjs/plugin/timezone";
import utcPlugin from "dayjs/plugin/utc";
import { cmd } from "@/utils/fetchUtils";
import PageHeader from "@/components/shared/PageHeader";
import { demoHistoricalLogs, isFakeMode } from "@/mirage/demo-data";
import downloadLogs from "./download";
import GameLogsFilters from "./GameLogsFilters";
import GameLogsTimeline from "./GameLogsTimeline";
import { filterLogsByCategory } from "./event-utils";

dayjs.extend(timezonePlugin);
dayjs.extend(utcPlugin);

const filterDemoLogs = (logs, fields) => {
  const nameQuery = fields.player_name.toLowerCase();
  const actionQuery = fields.action.toUpperCase();
  const playerMatches = (value) =>
    fields.exact_player
      ? String(value || "").toLowerCase() === nameQuery
      : String(value || "")
          .toLowerCase()
          .includes(nameQuery);
  const actionMatches = (value) =>
    fields.exact_action
      ? String(value || "").toUpperCase() === actionQuery
      : String(value || "")
          .toUpperCase()
          .includes(actionQuery);

  return logs
    .filter((log) =>
      !nameQuery
        ? true
        : playerMatches(log.player1_name) || playerMatches(log.player2_name)
    )
    .filter((log) =>
      !fields.player_id
        ? true
        : [log.player1_id, log.player2_id].includes(fields.player_id)
    )
    .filter((log) => (!actionQuery ? true : actionMatches(log.type)))
    .filter((log) =>
      !fields.server_filter
        ? true
        : String(log.server) === String(fields.server_filter)
    )
    .filter((log) =>
      !fields.from ? true : dayjs(log.event_time).isAfter(fields.from)
    )
    .filter((log) =>
      !fields.till ? true : dayjs(log.event_time).isBefore(fields.till)
    )
    .sort((a, b) => {
      const delta =
        dayjs(a.event_time).valueOf() - dayjs(b.event_time).valueOf();
      return fields.time_sort === "asc" ? delta : -delta;
    })
    .slice(0, fields.limit);
};

export const loader = async ({ request }) => {
  const url = new URL(request.url);
  const player_name = url.searchParams.get("player_name") ?? "";
  const player_id = url.searchParams.get("player_id") ?? "";
  const action = url.searchParams.get("action") ?? "";
  const from = url.searchParams.get("from")
    ? dayjs(url.searchParams.get("from"))
    : null;
  const till = url.searchParams.get("till")
    ? dayjs(url.searchParams.get("till"))
    : null;
  const limit = url.searchParams.get("limit")
    ? Number(url.searchParams.get("limit"))
    : 500;
  const time_sort = url.searchParams.get("time_sort") ?? "desc";
  const exact_player = url.searchParams.get("exact_player") === "true";
  const exact_action = url.searchParams.get("exact_action") === "true";
  const server_filter = url.searchParams.get("server_filter") ?? "";

  const fields = {
    player_name,
    action,
    player_id,
    from,
    till,
    limit,
    time_sort,
    exact_player,
    exact_action,
    server_filter,
  };

  const response = isFakeMode()
    ? { result: filterDemoLogs(demoHistoricalLogs, fields) }
    : await cmd.GET_HISTORICAL_LOGS({ payload: fields });

  return { logs: response.result || [], fields };
};

const isPlayerId = (value) => /^(?:\d{17}|[A-Z0-9]{16})$/i.test(value);

const GameLogsPage = () => {
  const { t } = useTranslation();
  const { logs, fields } = useLoaderData();
  const submit = useSubmit();
  const [category, setCategory] = useState("all");
  const filteredLogs = useMemo(
    () => filterLogsByCategory(logs || [], category),
    [logs, category]
  );

  const handleSubmit = (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const playerQuery = String(formData.get("player_query") || "").trim();
    formData.delete("player_query");
    formData.set("player_name", isPlayerId(playerQuery) ? "" : playerQuery);
    formData.set("player_id", isPlayerId(playerQuery) ? playerQuery : "");

    if (
      !formData.get("server_filter") ||
      formData.get("server_filter") === "0"
    ) {
      formData.set("server_filter", "");
    }

    [...formData.entries()].forEach(([key, value]) => {
      if (value === "") formData.delete(key);
    });

    submit(Object.fromEntries(formData), { method: "GET", replace: true });
  };

  const handleReset = () => {
    submit({ limit: 500, time_sort: "desc" }, { method: "GET", replace: true });
  };

  return (
    <Stack spacing={1} sx={{ mt: 0.5, width: "100%", minWidth: 0, pb: 2 }}>
      <PageHeader
        eyebrow={t("records.gameLogs.eyebrow")}
        title={t("records.gameLogs.title")}
        subtitle={t("records.gameLogs.timeline.subtitle")}
        actions={
          <Stack direction="row" alignItems="center" spacing={1.5}>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ whiteSpace: "nowrap" }}
            >
              {t("records.gameLogs.timeline.loaded", { count: logs.length })}
            </Typography>
            <Button
              variant="outlined"
              startIcon={<DownloadIcon />}
              onClick={() => downloadLogs(logs)}
              sx={{ borderRadius: 0, whiteSpace: "nowrap" }}
            >
              {t("records.gameLogs.timeline.export")}
            </Button>
          </Stack>
        }
      />

      <GameLogsFilters
        fields={fields}
        logs={logs}
        category={category}
        onCategoryChange={setCategory}
        onSubmit={handleSubmit}
        onReset={handleReset}
      />

      <Box sx={{ minWidth: 0 }}>
        <GameLogsTimeline
          logs={filteredLogs}
          allLogs={logs}
          category={category}
          onCategoryChange={setCategory}
        />
      </Box>
    </Stack>
  );
};

export default GameLogsPage;
