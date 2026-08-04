import Table from "@/components/table/Table";
import {
  Stack,
  Typography,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Divider,
  Box,
} from "@mui/material";
import { memo, useState } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  getFilteredRowModel,
} from "@tanstack/react-table";
import { TableToolbar } from "@/components/table/TableToolbar";
import { DebouncedSearchInput } from "@/components/shared/DebouncedSearchInput";
import { TablePagination } from "@/components/table/TablePagination";
import ConfirmButton from "@/components/shared/ConfirmButton";
import { useTranslation } from "react-i18next";

const VipTable = memo(
  ({
    data,
    columns,
    isLoading,
    isFetching,
    handleBulkRemove,
    editSelected,
  }) => {
    const { t } = useTranslation();
    const [pagination, setPagination] = useState({
      pageIndex: 0,
      pageSize: 50,
    });
    const [globalFilter, setGlobalFilter] = useState("");
    const [columnVisibility, setColumnVisibility] = useState({
      player_id: false,
    });
    const [columnFilters, setColumnFilters] = useState([
      { id: "status", value: "" },
    ]);

    const table = useReactTable({
      data: data || [],
      columns,
      getCoreRowModel: getCoreRowModel(),
      getPaginationRowModel: getPaginationRowModel(),
      getSortedRowModel: getSortedRowModel(),
      getFilteredRowModel: getFilteredRowModel(),
      onPaginationChange: setPagination,
      onGlobalFilterChange: setGlobalFilter,
      onColumnVisibilityChange: setColumnVisibility,
      onFiltersChange: setColumnFilters,
      globalFilterFn: "includesString",
      state: {
        pagination,
        globalFilter,
        columnVisibility,
        filters: columnFilters,
      },
    });

    const rowsCount = table.getRowCount();
    const selectedRows = table.getSelectedRowModel().rows.length;

    return (
      <Stack
        component="section"
        sx={{ width: "100%", bgcolor: "background.paper" }}
      >
        <Stack
          direction="row"
          alignItems="center"
          spacing={1}
          sx={{ width: "100%", p: 1 }}
        >
          <Button
            disabled={selectedRows === 0 || isFetching}
            variant="contained"
            color="primary"
            size="small"
            onClick={() => editSelected(table)}
          >
            {t("records.vips.editSelected")}
          </Button>
          <ConfirmButton
            buttonText={t("records.vips.removeSelected")}
            title={t("records.vips.removeSelectedTitle")}
            description={t("records.vips.removeSelectedDescription", { count: selectedRows })}
            onConfirm={() => handleBulkRemove(table)}
            disabled={selectedRows === 0 || isFetching}
            buttonProps={{
              variant: "contained",
              color: "error",
              size: "small",
            }}
          />
        </Stack>
        <TableToolbar>
          <Stack
            direction="row"
            alignItems="center"
            spacing={1}
            sx={{ width: "100%", p: 1 }}
          >
            <DebouncedSearchInput
              placeholder={t("records.vips.search")}
              onChange={(value) => {
                setGlobalFilter(value);
              }}
            />
            <Box sx={{ flexGrow: 1 }} />
            <StatusFilter
              value={
                table
                  .getState()
                  .columnFilters.find((filter) => filter.id === "status")?.value
              }
              onChange={(value) => {
                table.setColumnFilters([{ id: "status", value }]);
              }}
            />
          </Stack>
          <Divider orientation="horizontal" flexItem sx={{ width: "100%" }} />
          <Stack
            direction="row"
            alignItems="center"
            flexWrap="wrap"
            spacing={2}
            sx={{ width: "100%", p: 1 }}
          >
            <Typography variant="body2">
              {t("records.vips.selection", { selected: selectedRows, total: rowsCount })}
            </Typography>
            <Box sx={{ flexGrow: 1 }} />
            <TablePagination table={table} />
          </Stack>
        </TableToolbar>
        <Table table={table} isLoading={isLoading} isFetching={isFetching} />
      </Stack>
    );
  }
);

export const StatusFilter = ({ value, onChange }) => {
  const { t } = useTranslation();
  return (
    <FormControl sx={{ minWidth: 120 }} size="small">
      <InputLabel id="status-filter-label">{t("records.vips.status")}</InputLabel>
      <Select
        labelId="status-filter-label"
        id="status-filter"
        value={value || ""}
        label={t("records.vips.status")}
        onChange={(event) => onChange(event.target.value)}
      >
        <MenuItem value="">
          <em>{t("records.vips.all")}</em>
        </MenuItem>
        <MenuItem value="active">{t("records.vips.active")}</MenuItem>
        <MenuItem value="expired">{t("records.vips.expired")}</MenuItem>
      </Select>
    </FormControl>
  );
};

export default VipTable;
