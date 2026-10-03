import { memo, useMemo, useState } from "react";
import {
  Box,
  Button,
  Checkbox,
  Divider,
  IconButton,
  Stack,
  Typography,
} from "@mui/material";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import DeleteOutlineOutlinedIcon from "@mui/icons-material/DeleteOutlineOutlined";
import PersonOutlineOutlinedIcon from "@mui/icons-material/PersonOutlineOutlined";
import CloseOutlinedIcon from "@mui/icons-material/CloseOutlined";
import KeyboardArrowDownOutlinedIcon from "@mui/icons-material/KeyboardArrowDownOutlined";
import KeyboardArrowUpOutlinedIcon from "@mui/icons-material/KeyboardArrowUpOutlined";
import dayjs from "dayjs";
import {
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useTranslation } from "react-i18next";
import Table from "@/components/table/Table";
import { TablePagination } from "@/components/table/TablePagination";
import ConfirmButton from "@/components/shared/ConfirmButton";
import CopyableText from "@/components/shared/CopyableText";
import getVipColumns, { StatusCell } from "./vip-columns";
import { getVipRemainingLabel, isVipIndefinite } from "./vip-utils";

const DetailMetric = ({ label, children }) => (
  <Box sx={{ minWidth: 0 }}>
    <Typography
      variant="caption"
      color="text.secondary"
      sx={{ display: "block", mb: 0.25, textTransform: "uppercase" }}
    >
      {label}
    </Typography>
    {children}
  </Box>
);

const VipRecordDetail = ({
  vip,
  mutationScope,
  onEdit,
  onRequestRemove,
  openProfile,
}) => {
  const { t } = useTranslation();
  return (
    <Box data-theme-surface="panel"
      sx={{
        m: { xs: 0, md: 0.75 },
        border: "1px solid",
        borderColor: "divider",
        borderLeft: "2px solid",
        borderLeftColor: "primary.main",
        bgcolor: "background.paper",
      }}
    >
      <Box sx={{ px: { xs: 1.5, md: 2 }, py: 1.25 }}>
        <Typography
          variant="overline"
          color="primary.main"
          sx={{ letterSpacing: "0.12em" }}
        >
          {t("records.vips.vipRecord")}
        </Typography>
      </Box>
      <Divider />
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr 1fr",
            sm: "repeat(4, minmax(0, 1fr))",
          },
          gap: { xs: 1.5, md: 2 },
          px: { xs: 1.5, md: 2 },
          py: 1.5,
        }}
      >
        <DetailMetric label={t("records.vips.player")}>
          <Typography variant="body2" noWrap>
            {vip.name}
          </Typography>
          <CopyableText
            text={vip.player_id}
            size="0.7em"
            sx={{ fontSize: "0.7em", color: "text.secondary" }}
          />
        </DetailMetric>
        <DetailMetric label={t("records.vips.status")}>
          <StatusCell expiration={vip.vip_expiration} t={t} />
        </DetailMetric>
        <DetailMetric label={t("records.vips.relativeExpiration")}>
          <Typography variant="body2">
            {getVipRemainingLabel(vip.vip_expiration, t)}
          </Typography>
        </DetailMetric>
        <DetailMetric label={t("records.vips.expirationExact")}>
          <Typography variant="body2">
            {isVipIndefinite(vip.vip_expiration)
              ? t("records.vips.indefinite")
              : dayjs(vip.vip_expiration).format("LLL")}
          </Typography>
        </DetailMetric>
      </Box>
      <Divider />
      <Stack
        direction={{ xs: "column", sm: "row" }}
        alignItems={{ xs: "stretch", sm: "center" }}
        justifyContent="space-between"
        gap={1}
        sx={{ px: { xs: 1.5, md: 2 }, py: 1.25 }}
      >
        <Typography variant="caption" color="text.secondary">
          {t("records.vips.scopeHint", {
            scope:
              mutationScope === "multi"
                ? t("records.vips.allServers")
                : t("records.vips.thisServer"),
          })}
        </Typography>
        <Stack direction="row" flexWrap="wrap" gap={0.75}>
          <Button
            size="small"
            variant="outlined"
            startIcon={<PersonOutlineOutlinedIcon />}
            onClick={() => openProfile(vip.player_id)}
          >
            {t("records.vips.profile")}
          </Button>
          <Button
            size="small"
            variant="contained"
            startIcon={<EditOutlinedIcon />}
            onClick={() => onEdit(vip)}
          >
            {t("records.vips.edit")}
          </Button>
          <Button
            size="small"
            variant="outlined"
            color="error"
            startIcon={<DeleteOutlineOutlinedIcon />}
            onClick={() => onRequestRemove(vip)}
          >
            {t("records.vips.remove")}
          </Button>
        </Stack>
      </Stack>
    </Box>
  );
};

const VipMobileRow = ({
  row,
  isFetching,
  mutationScope,
  onEdit,
  onRequestRemove,
  openProfile,
}) => {
  const { t } = useTranslation();
  const vip = row.original;

  return (
    <Box
      sx={{
        borderBottom: "1px solid",
        borderColor: "divider",
        bgcolor: row.getIsExpanded() ? "action.selected" : "transparent",
      }}
    >
      <Stack direction="row" alignItems="center" gap={1} sx={{ p: 1 }}>
        <Checkbox
          checked={row.getIsSelected()}
          onChange={row.getToggleSelectedHandler()}
          disabled={isFetching}
          inputProps={{
            "aria-label": t("records.vips.selectPlayer", { name: vip.name }),
          }}
          sx={{ p: 0.75 }}
        />
        <Box minWidth={0} flex={1}>
          <Typography
            component="button"
            type="button"
            variant="body2"
            onClick={() => openProfile(vip.player_id)}
            sx={{
              border: 0,
              bgcolor: "transparent",
              color: "text.primary",
              p: 0,
              font: "inherit",
              maxWidth: "100%",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {vip.name}
          </Typography>
          <Typography
            variant="caption"
            color="text.secondary"
            noWrap
            display="block"
          >
            {getVipRemainingLabel(vip.vip_expiration, t)}
          </Typography>
        </Box>
        <StatusCell expiration={vip.vip_expiration} t={t} />
        <IconButton
          onClick={row.getToggleExpandedHandler()}
          aria-label={
            row.getIsExpanded()
              ? t("records.vips.collapseDetails", { name: vip.name })
              : t("records.vips.expandDetails", { name: vip.name })
          }
          sx={{ borderRadius: 0 }}
        >
          {row.getIsExpanded() ? (
            <KeyboardArrowUpOutlinedIcon />
          ) : (
            <KeyboardArrowDownOutlinedIcon />
          )}
        </IconButton>
      </Stack>
      {row.getIsExpanded() ? (
        <VipRecordDetail
          vip={vip}
          mutationScope={mutationScope}
          onEdit={onEdit}
          onRequestRemove={onRequestRemove}
          openProfile={openProfile}
        />
      ) : null}
    </Box>
  );
};

const VipTable = memo(function VipTable({
  data,
  totalCount,
  isLoading,
  isFetching,
  mutationScope,
  onEdit,
  onRequestRemove,
  onBulkEdit,
  onBulkRemove,
  openProfile,
}) {
  const { t } = useTranslation();
  const [pagination, setPagination] = useState({ pageIndex: 0, pageSize: 50 });
  const [rowSelection, setRowSelection] = useState({});
  const [expanded, setExpanded] = useState({});

  const columns = useMemo(
    () =>
      getVipColumns({
        t,
        isFetching,
        openProfile,
        onEdit,
        onRequestRemove,
      }),
    [isFetching, onEdit, onRequestRemove, openProfile, t]
  );

  const table = useReactTable({
    data: data || [],
    columns,
    getRowId: (row) => row.player_id,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getRowCanExpand: () => true,
    onPaginationChange: setPagination,
    onRowSelectionChange: setRowSelection,
    onExpandedChange: setExpanded,
    state: { pagination, rowSelection, expanded },
  });

  const selectedRows = table.getSelectedRowModel().rows.length;
  const visibleRows = table.getRowModel().rows;

  return (
    <Stack data-theme-surface="panel"
      component="section"
      aria-label={t("records.vips.register")}
      sx={{ minWidth: 0, border: "1px solid", borderColor: "divider" }}
    >
      <Stack
        direction={{ xs: "column", sm: "row" }}
        alignItems={{ xs: "stretch", sm: "center" }}
        justifyContent="space-between"
        gap={1}
        sx={{ px: 1.25, py: 0.75, minHeight: 46, bgcolor: "background.paper" }}
      >
        <Typography variant="body2" color="text.secondary">
          {t("records.vips.resultCount", {
            shown: data?.length || 0,
            total: totalCount,
          })}
        </Typography>
        <TablePagination table={table} />
      </Stack>
      <Divider />

      <Box sx={{ display: { xs: "none", md: "block" } }}>
        <Table
          table={table}
          config={{ density: "dense", fontSize: "small" }}
          isLoading={isLoading}
          isFetching={isFetching}
          rowProps={(row) => ({
            "data-inspected": row.getIsExpanded() ? "true" : undefined,
          })}
          renderSubComponent={({ row }) => (
            <VipRecordDetail
              vip={row.original}
              mutationScope={mutationScope}
              onEdit={onEdit}
              onRequestRemove={onRequestRemove}
              openProfile={openProfile}
            />
          )}
        />
      </Box>

      <Box sx={{ display: { xs: "block", md: "none" } }}>
        {visibleRows.map((row) => (
          <VipMobileRow
            key={row.id}
            row={row}
            isFetching={isFetching}
            mutationScope={mutationScope}
            onEdit={onEdit}
            onRequestRemove={onRequestRemove}
            openProfile={openProfile}
          />
        ))}
      </Box>

      {selectedRows > 0 ? (
        <Stack
          direction={{ xs: "column", sm: "row" }}
          alignItems={{ xs: "stretch", sm: "center" }}
          gap={1}
          sx={{
            position: "sticky",
            bottom: 0,
            zIndex: 5,
            px: 1.5,
            py: 1,
            borderTop: "1px solid",
            borderColor: "primary.main",
            bgcolor: "background.paper",
          }}
        >
          <Typography
            variant="subtitle2"
            color="primary.main"
            sx={{ mr: "auto" }}
          >
            {t("records.vips.selectedCount", { count: selectedRows })}
          </Typography>
          <Button
            size="small"
            variant="contained"
            startIcon={<EditOutlinedIcon />}
            onClick={() => onBulkEdit(table)}
            disabled={isFetching}
          >
            {t("records.vips.editSelected")}
          </Button>
          <ConfirmButton
            buttonText={t("records.vips.removeSelected")}
            title={t("records.vips.removeSelectedTitle")}
            description={t("records.vips.removeSelectedDescription", {
              count: selectedRows,
            })}
            onConfirm={() => onBulkRemove(table)}
            disabled={isFetching}
            buttonProps={{
              size: "small",
              variant: "outlined",
              color: "error",
              startIcon: <DeleteOutlineOutlinedIcon />,
            }}
          />
          <Button
            size="small"
            startIcon={<CloseOutlinedIcon />}
            onClick={() => table.resetRowSelection()}
          >
            {t("records.vips.clearSelection")}
          </Button>
        </Stack>
      ) : null}
    </Stack>
  );
});

export default VipTable;
