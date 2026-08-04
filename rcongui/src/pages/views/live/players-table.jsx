import Table from "@/components/table/Table";
import TableConfigDrawer from "@/components/table/TableConfigDrawer";
import { Box, Divider, IconButton, Stack } from "@mui/material";
import { memo, useState } from "react";
import { DebouncedSearchInput } from "@/components/shared/DebouncedSearchInput";
import SettingsIcon from "@mui/icons-material/Settings";
import UnfoldMoreIcon from "@mui/icons-material/UnfoldMore";
import UnfoldLessIcon from "@mui/icons-material/UnfoldLess";
import { TeamSelectionToolbar } from "./TeamSelectionToolbar";
import { ActionMenuButton } from "@/features/player-action/ActionMenu";
import { generatePlayerActions } from "@/features/player-action/actions";
import TableColumnSelection from "@/components/table/TableColumnSelection";
import { TableToolbar } from "@/components/table/TableToolbar";
import { usePlayersTableStore } from "@/stores/table-config";
import { useTranslation } from "react-i18next";

const PlayersTable = ({ table, teamData, selectedPlayers, onColumnVisibilityChange, isFetching }) => {
  const { t } = useTranslation();
  const [tableConfigDrawerOpen, setTableConfigDrawerOpen] = useState(false);
  
  const tableConfig = usePlayersTableStore();
  const setConfig = usePlayersTableStore(state => state.setConfig);
  const setExpandedView = usePlayersTableStore(state => state.setExpandedView);

  const handleTableConfigClick = () => {
    setTableConfigDrawerOpen(prev => !prev);
  };

  return (
    <>
      <TeamSelectionToolbar table={table} teamData={teamData} />
      <Stack direction="column" spacing={0}>
        <TableToolbar>
          <ActionMenuButton
            actions={generatePlayerActions({
              multiAction: true,
              onlineAction: true,
            })}
            disabled={
              !table.getIsSomePageRowsSelected() &&
              !table.getIsAllRowsSelected()
            }
            recipients={selectedPlayers}
            orientation="horizontal"
            disableRipple={true}
            sx={{
              p: "1px 4px",
              height: "100%",
            }}
          />
          <DebouncedSearchInput
            placeholder={t("views.team.searchPlayer")}
            initialValue={table.getColumn("name")?.getFilterValue() ?? ""}
            onChange={(value) => {
              table.getColumn("name")?.setFilterValue(value);
            }}
          />
          <Box sx={{ flexGrow: 1 }} />
          <Divider flexItem orientation="vertical" sx={{ marginLeft: 0, marginRight: 0 }} />
          <IconButton
            size="small"
            aria-label={tableConfig.expandedView ? t("common.collapse") : t("common.expand")}
            aria-description={
              tableConfig.expandedView
                ? t("views.table.collapseDetails")
                : t("views.table.expandDetails")
            }
            sx={{ p: 0.5, borderRadius: 0 }}
            onClick={() => {
              setExpandedView(!tableConfig.expandedView);
            }}
          >
            {tableConfig.expandedView ? (
              <UnfoldLessIcon sx={{ fontSize: "1rem" }} />
            ) : (
              <UnfoldMoreIcon sx={{ fontSize: "1rem" }} />
            )}
          </IconButton>
          <TableColumnSelection table={table} onColumnVisibilityChange={onColumnVisibilityChange} />
          <IconButton
            size="small"
            aria-label={t("common.settings")}
            aria-description={t("common.settings")}
            sx={{ p: 0.5, borderRadius: 0 }}
            onClick={handleTableConfigClick}
          >
            <SettingsIcon sx={{ fontSize: "1rem" }} />
          </IconButton>
        </TableToolbar>
        <Table table={table} config={tableConfig} isFetching={isFetching} />
      </Stack>
      <TableConfigDrawer
        name={t("views.live.players")}
        open={tableConfigDrawerOpen}
        onClose={(config) => {
          setTableConfigDrawerOpen(false);
          setConfig(config);
        }}
        config={tableConfig}
      />
    </>
  );
};

export default memo(PlayersTable);
