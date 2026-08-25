import { DebouncedSearchInput } from "@/components/shared/DebouncedSearchInput";
import Table from "@/components/table/Table";
import { TableToolbar } from "@/components/table/TableToolbar";
import { Box, Divider, IconButton } from "@mui/material";
import { useState } from "react";
import SettingsIcon from "@mui/icons-material/Settings";
import TableConfigDrawer from "@/components/table/TableConfigDrawer";
import NavPagination from "./nav-pagination";
import { useGameListTableStore } from "@/stores/table-config";
import { useTranslation } from "react-i18next";
import { ButtonBase, Paper, Stack, Typography, useMediaQuery, useTheme } from "@mui/material";
import { Link } from "react-router-dom";
import { getGameDuration } from "@/utils/lib";
import { getMapEnvironmentLabel, getMapModeLabel } from "@/utils/mapLabels";

export function GameListTable({ table, maxPages, page }) {
  const { t } = useTranslation();
  const [tableConfigDrawerOpen, setTableConfigDrawerOpen] = useState(false);
  const tableConfig = useGameListTableStore();
  const setConfig = useGameListTableStore(state => state.setConfig);
  const theme = useTheme();
  const compact = useMediaQuery(theme.breakpoints.down("md"));

  const handleTableConfigClick = () => {
    // toggle config drawer
    setTableConfigDrawerOpen((prev) => !prev);
  };

  return (
    <Box>
      <TableToolbar sx={compact ? { flexWrap: "wrap", gap: 1 } : undefined}>
        <DebouncedSearchInput
          placeholder={t("stats.games.search")}
          onChange={(value) => {
            // set global filter
            table.getColumn("map").setFilterValue(String(value));
          }}
          sx={{ maxWidth: compact ? "none" : 230, flex: compact ? "1 1 100%" : undefined }}
        />
        <NavPagination page={page} maxPages={maxPages} />
        {!compact && <Divider flexItem orientation="vertical" />}
        {!compact && <IconButton
          size="small"
          sx={{ width: 20, height: 20, borderRadius: 0, p: 2 }}
          onClick={handleTableConfigClick}
        >
          <SettingsIcon sx={{ fontSize: 16 }} />
        </IconButton>}
      </TableToolbar>
      {compact ? (
        <Stack component="section" aria-label={t("stats.games.title")} gap={1} sx={{ mt: 1 }}>
          {table.getRowModel().rows.map(({ original: game }) => (
            <ButtonBase
              key={game.id}
              component={Link}
              to={`/stats/games/${game.id}`}
              sx={{ display: "block", textAlign: "left", width: "100%" }}
            >
              <Paper
                variant="outlined"
                sx={{
                  display: "grid",
                  gridTemplateColumns: "72px minmax(0, 1fr) auto",
                  gap: 1.25,
                  alignItems: "center",
                  width: "100%",
                  minHeight: 76,
                  p: 1,
                  borderRadius: 0,
                  "&:hover": { borderColor: "primary.main", bgcolor: "action.hover" },
                }}
              >
                <Box
                  component="img"
                  src={`/maps/icons/${game.map.image_name}`}
                  alt=""
                  sx={{ width: 72, height: 48, objectFit: "cover", border: "1px solid", borderColor: "divider" }}
                />
                <Box sx={{ minWidth: 0 }}>
                  <Typography sx={{ fontWeight: 800 }} noWrap>
                    {game.map.map.pretty_name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" noWrap>
                    {getMapModeLabel(t, game.map.game_mode)} · {getMapEnvironmentLabel(t, game.map.environment)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" display="block">
                    {getGameDuration(game.start, game.end)}
                  </Typography>
                </Box>
                <Stack alignItems="flex-end" sx={{ px: 0.5 }}>
                  <Typography variant="overline" color="text.secondary" sx={{ lineHeight: 1 }}>
                    {t("stats.games.result")}
                  </Typography>
                  <Typography variant="h6" color="primary.main" sx={{ fontWeight: 800, whiteSpace: "nowrap" }}>
                    {game.result?.allied ?? "?"} : {game.result?.axis ?? "?"}
                  </Typography>
                </Stack>
              </Paper>
            </ButtonBase>
          ))}
        </Stack>
      ) : <Table table={table} config={tableConfig} />}
      <TableConfigDrawer
        name={t("stats.games.listSettings")}
        open={tableConfigDrawerOpen}
        onClose={(config) => {
          setTableConfigDrawerOpen(false);
          setConfig(config);
        }}
        config={tableConfig}
      />
    </Box>
  );
}
