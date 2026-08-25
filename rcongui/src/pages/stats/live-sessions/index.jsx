import {
  Box,
  ButtonBase,
  Checkbox,
  Collapse,
  IconButton,
  Paper,
  Stack,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import { useMemo, useState } from "react";
import { teamsLiveQuery } from "@/queries/teams-live-query";
import {
  getExpandedRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { getCoreRowModel } from "@tanstack/react-table";
import { createLiveSessionColumns } from "./columns";
import Table from "@/components/table/Table";
import { isLeader, normalizePlayerProfile } from "@/utils/lib";
import { extractPlayers } from "@/utils/extractPlayers";
import { TableToolbar } from "@/components/table/TableToolbar";
import { ActionMenuButton } from "@/features/player-action/ActionMenu";
import { DebouncedSearchInput } from "@/components/shared/DebouncedSearchInput";
import { generatePlayerActions } from "@/features/player-action/actions";
import { useLiveSessionsTableStore } from "@/stores/table-config";
import TableConfigDrawer from "@/components/table/TableConfigDrawer";
import SettingsIcon from "@mui/icons-material/Settings";
import { useTranslation } from "react-i18next";
import PageHeader from "@/components/shared/PageHeader";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import GroupsIcon from "@mui/icons-material/Groups";
import { getColoredFactionIconSrc } from "@/utils/lib";
import { NoRowsOverlay } from "@/components/NoRowsOverlay";

const LiveSessionsPage = () => {
  const { t } = useTranslation();
  const theme = useTheme();
  const compact = useMediaQuery(theme.breakpoints.down("md"));
  const { data } = teamsLiveQuery({ refetchInterval: 15 * 1000 });
  const columns = useMemo(() => createLiveSessionColumns(t), [t]);
  const multiPlayerActions = useMemo(
    () => generatePlayerActions({ multiAction: true, onlineAction: true }),
    []
  );
  const singlePlayerActions = useMemo(
    () => generatePlayerActions({ multiAction: false, onlineAction: true }),
    []
  );

  const tableConfig = useLiveSessionsTableStore();
  const [tableConfigDrawerOpen, setTableConfigDrawerOpen] = useState(false);
  const setConfig = useLiveSessionsTableStore(state => state.setConfig);

  const playersData = useMemo(() => {
    if (!data) return [];

    const players = extractPlayers(data).map((player) => ({
      ...player,
      profile: normalizePlayerProfile(player?.profile),
    }));

    const teams = players.reduce(
      (acc, player) => {
        let [teamName, unitName] = [player.team, player.unit_name];
        teamName =
          teamName !== "axis" && teamName !== "allies" ? "neutral" : teamName;
        if (!acc[teamName][unitName]) {
          acc[teamName][unitName] = {
            players: [],
            leader: null,
            unitName,
            teamName,
          };
        }
        acc[teamName][unitName].players.push(player);
        if (!acc[teamName][unitName].leader && isLeader(player.role)) {
          acc[teamName][unitName].leader = player;
        }
        return acc;
      },
      { axis: {}, allies: {}, neutral: {} }
    );

    const teamsRows = Object.values(teams).map((team) =>
      Object.values(team).map((unit) => {
        let unitData = {};
        if (unit.teamName !== "neutral") {
          unitData =
            unit.unitName !== "commmand"
              ? data[unit.teamName]["squads"][unit.unitName]
              : { type: "armycommander" };
        }

        const unitLeader = unit.leader ?? {
          profile: normalizePlayerProfile({}),
          name: unit.teamName === "neutral" ? t("stats.liveSessions.unassigned") : t("stats.liveSessions.noLeader"),
          unit_name: unit.unitName,
          team: unit.teamName,
          role: "",
          level: 0,
          time: 0,
        };

        return {
          ...unitLeader,
          ...unitData,
          subrows: unit.players,
        };
      })
    );

    return teamsRows.reduce((acc, team) => [...acc, ...team], []);
  }, [data, t]);

  const table = useReactTable({
    data: playersData,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSubRows: (row) => row.subrows,
  });

  return (
    <Box>
      <PageHeader
        eyebrow={t("stats.liveSessions.eyebrow")}
        title={t("stats.liveSessions.title")}
        subtitle={t("stats.liveSessions.subtitle")}
      />
      {compact ? (
        <Stack
          direction="row"
          alignItems="center"
          gap={0.5}
          sx={{
            mt: 2,
            border: "1px solid",
            borderColor: "divider",
            p: 0.5,
          }}
        >
          <DebouncedSearchInput
            placeholder={t("stats.liveSessions.searchPlayer")}
            initialValue={table.getColumn("name")?.getFilterValue() ?? ""}
            onChange={(value) => table.getColumn("name")?.setFilterValue(value)}
            sx={{ flex: 1, minWidth: 0 }}
          />
          <ActionMenuButton
            actions={multiPlayerActions}
            disabled={
              !table.getIsSomePageRowsSelected() && !table.getIsAllRowsSelected()
            }
            recipients={table.getSelectedRowModel().rows.map((row) => row.original)}
            orientation="horizontal"
            disableRipple
            sx={{ minWidth: 44, minHeight: 44 }}
          />
          <IconButton
            aria-label={t("common.settings")}
            sx={{ minWidth: 44, minHeight: 44, borderRadius: 0 }}
            onClick={() => setTableConfigDrawerOpen(true)}
          >
            <SettingsIcon sx={{ fontSize: "1rem" }} />
          </IconButton>
        </Stack>
      ) : (
        <TableToolbar table={table}>
          <ActionMenuButton
            actions={multiPlayerActions}
            disabled={
              !table.getIsSomePageRowsSelected() && !table.getIsAllRowsSelected()
            }
            recipients={table.getSelectedRowModel().rows.map((row) => row.original)}
            orientation="horizontal"
            disableRipple
            sx={{ p: "1px 4px", height: "100%" }}
          />
          <DebouncedSearchInput
            placeholder={t("stats.liveSessions.searchPlayer")}
            initialValue={table.getColumn("name")?.getFilterValue() ?? ""}
            onChange={(value) => table.getColumn("name")?.setFilterValue(value)}
            sx={{ maxWidth: "300px" }}
          />
          <IconButton
            size="small"
            sx={{ p: 0.5, borderRadius: 0 }}
            onClick={() => setTableConfigDrawerOpen(true)}
          >
            <SettingsIcon sx={{ fontSize: "1rem" }} />
          </IconButton>
        </TableToolbar>
      )}
      {compact ? (
        <Stack
          component="section"
          aria-label={t("stats.liveSessions.title")}
          gap={0}
          sx={{ mt: 1 }}
        >
          {table.getRowModel().rows.length === 0 && <NoRowsOverlay />}
          {table.getRowModel().rows.map((row) => {
            const player = row.original;
            const isUnit = row.getCanExpand();
            const expanded = row.getIsExpanded();
            const faction = player.faction ?? player.team;
            const memberCount = player.subrows?.length ?? 0;

            return (
              <Paper
                key={row.id}
                variant="outlined"
                sx={{
                  ml: row.depth ? 2.5 : 0,
                  borderRadius: 0,
                  borderBottomWidth: 0,
                  borderLeftColor: row.depth
                    ? faction === "axis"
                      ? "error.main"
                      : "info.main"
                    : "divider",
                  "&:last-child": { borderBottomWidth: 1 },
                }}
              >
                <Stack
                  direction="row"
                  alignItems="center"
                  sx={{ minHeight: isUnit ? 56 : 52, pr: 0.5 }}
                >
                  <Checkbox
                    checked={row.getIsSelected()}
                    disabled={!row.getCanSelect()}
                    indeterminate={row.getIsSomeSelected()}
                    onChange={row.getToggleSelectedHandler()}
                    inputProps={{
                      "aria-label": t("common.selectPlayer", {
                        name: player.name,
                      }),
                    }}
                    size="small"
                    sx={{ minWidth: 44, minHeight: 44 }}
                  />
                  <ButtonBase
                    aria-expanded={isUnit ? expanded : undefined}
                    aria-label={
                      isUnit
                        ? `${player.unit_name ?? player.name} ${
                            expanded ? t("common.close") : t("common.open")
                          }`
                        : undefined
                    }
                    onClick={isUnit ? row.getToggleExpandedHandler() : undefined}
                    sx={{
                      display: "grid",
                      gridTemplateColumns: "30px minmax(0, 1fr) 42px 42px 44px",
                      alignItems: "center",
                      flex: 1,
                      minWidth: 0,
                      minHeight: isUnit ? 56 : 52,
                      textAlign: "left",
                    }}
                  >
                    {isUnit ? (
                      <ChevronRightIcon
                        sx={{
                          transform: expanded ? "rotate(90deg)" : "none",
                          transition: "transform 120ms",
                        }}
                      />
                    ) : faction ? (
                      <Box
                        component="img"
                        src={getColoredFactionIconSrc(faction)}
                        alt={faction}
                        sx={{ width: 18, height: 18 }}
                      />
                    ) : (
                      <Box />
                    )}
                    <Box sx={{ minWidth: 0 }}>
                      <Typography noWrap sx={{ fontWeight: 800 }}>
                        {isUnit
                          ? player.unit_name ?? player.name
                          : player.name}
                      </Typography>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        noWrap
                        display="block"
                      >
                        {isUnit
                          ? `${memberCount} · ${player.name}`
                          : `${player.unit_name ?? "–"} · ${player.role ?? "–"}`}
                      </Typography>
                    </Box>
                    <Box sx={{ textAlign: "center" }}>
                      <Typography variant="caption" color="text.secondary" display="block">
                        {t("stats.liveSessions.level")}
                      </Typography>
                      <Typography sx={{ fontWeight: 800 }}>{player.level ?? 0}</Typography>
                    </Box>
                    <Box sx={{ textAlign: "center" }}>
                      <Typography variant="caption" color="text.secondary" display="block">
                        K
                      </Typography>
                      <Typography sx={{ fontWeight: 800 }}>{player.kills ?? 0}</Typography>
                    </Box>
                    <Box sx={{ textAlign: "center" }}>
                      <Typography variant="caption" color="text.secondary" display="block">
                        T
                      </Typography>
                      <Typography sx={{ fontWeight: 800 }}>{player.deaths ?? 0}</Typography>
                    </Box>
                  </ButtonBase>
                  {!isUnit && (
                    <ActionMenuButton
                      actions={singlePlayerActions}
                      recipients={player}
                      orientation="horizontal"
                      disableRipple
                      sx={{ minWidth: 44, minHeight: 44 }}
                    />
                  )}
                </Stack>
                {isUnit && (
                  <Collapse in={expanded} unmountOnExit>
                    <Stack
                      direction="row"
                      alignItems="center"
                      gap={1}
                      sx={{
                        px: 1.5,
                        py: 1,
                        borderTop: "1px solid",
                        borderColor: "divider",
                        bgcolor: "background.default",
                      }}
                    >
                      <GroupsIcon color="action" fontSize="small" />
                      <Typography variant="caption" color="text.secondary">
                        {memberCount} · {player.team ?? t("common.unknown")}
                      </Typography>
                    </Stack>
                  </Collapse>
                )}
              </Paper>
            );
          })}
        </Stack>
      ) : (
        <Table table={table} config={tableConfig} />
      )}
      <TableConfigDrawer
        name={t("stats.liveSessions.tableSettings")}
        open={tableConfigDrawerOpen}
        onClose={(config) => {
          setTableConfigDrawerOpen(false);
          setConfig(config);
        }}
        config={tableConfig}
      />
    </Box>
  );
};

export default LiveSessionsPage;
