import { useCallback, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  ButtonBase,
  Collapse,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  FormControl,
  InputAdornment,
  LinearProgress,
  MenuItem,
  Select,
  Snackbar,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import AddOutlinedIcon from "@mui/icons-material/AddOutlined";
import ImportExportOutlinedIcon from "@mui/icons-material/ImportExportOutlined";
import SearchOutlinedIcon from "@mui/icons-material/SearchOutlined";
import RefreshOutlinedIcon from "@mui/icons-material/RefreshOutlined";
import FilterAltOutlinedIcon from "@mui/icons-material/FilterAltOutlined";
import PeopleAltOutlinedIcon from "@mui/icons-material/PeopleAltOutlined";
import PersonOutlineOutlinedIcon from "@mui/icons-material/PersonOutlineOutlined";
import ScheduleOutlinedIcon from "@mui/icons-material/ScheduleOutlined";
import AllInclusiveOutlinedIcon from "@mui/icons-material/AllInclusiveOutlined";
import ErrorOutlineOutlinedIcon from "@mui/icons-material/ErrorOutlineOutlined";
import {
  HydrationBoundary,
  QueryClient,
  dehydrate,
  useMutation,
  useQuery,
} from "@tanstack/react-query";
import dayjs from "dayjs";
import { useTranslation } from "react-i18next";
import { useLoaderData } from "react-router-dom";
import PageHeader from "@/components/shared/PageHeader";
import { usePlayerSidebar } from "@/hooks/usePlayerSidebar";
import { queryClient } from "@/queryClient";
import { vipMutationOptions, vipQueryOptions } from "@/queries/vip-query";
import debug from "@/utils/debug";
import VipEditorDialog from "./VipEditorDialog";
import VipTable from "./vip-table";
import VipTransferDialog from "./VipTransferDialog";
import { VipBulkEditDialog } from "./VipBulkEditDialog";
import {
  INDEFINITE_EXPIRATION,
  getVipCategory,
  isVipExpired,
  isVipExpiringSoon,
  isVipIndefinite,
} from "./vip-utils";

const logger = debug("VIP VIEW");
const VIP_QUERY_KEY = vipQueryOptions.list().queryKey;

const getMutationIssue = (response) => {
  if (response?.failed || response?.result?.failed) {
    return response?.error || response?.result?.error || "request_failed";
  }
  const forwarding =
    response?.forward_results || response?.result?.forward_results;
  if (
    forwarding &&
    Object.values(forwarding).some((result) => result?.failed)
  ) {
    return "partial_forward_failure";
  }
  return null;
};

const SummaryItem = ({
  icon,
  label,
  value,
  active,
  onClick,
  color,
  wideOnMobile = false,
}) => (
  <ButtonBase
    onClick={onClick}
    sx={{
      minWidth: 0,
      justifyContent: "flex-start",
      textAlign: "left",
      borderRight: { xs: 0, sm: "1px solid" },
      borderBottom: { xs: "1px solid", sm: 0 },
      borderColor: "divider",
      px: 1.75,
      py: 1.25,
      bgcolor: active ? "action.selected" : "transparent",
      boxShadow: active ? "inset 0 -2px 0" : "none",
      color: active ? "primary.main" : "text.primary",
      gridColumn: { xs: wideOnMobile ? "1 / -1" : "auto", sm: "auto" },
      "&:hover": { bgcolor: "action.hover" },
      "&:focus-visible": {
        outline: "2px solid",
        outlineColor: "primary.main",
        outlineOffset: -2,
      },
    }}
  >
    <Stack direction="row" alignItems="center" gap={1.25} minWidth={0}>
      <Box data-theme-surface="control"
        sx={{
          display: "grid",
          placeItems: "center",
          width: 34,
          height: 34,
          flex: "0 0 34px",
          border: "1px solid",
          borderColor: "divider",
          color,
        }}
      >
        {icon}
      </Box>
      <Box minWidth={0}>
        <Typography
          variant="caption"
          color="text.secondary"
          noWrap
          display="block"
        >
          {label}
        </Typography>
        <Typography variant="h6" lineHeight={1.05} color="text.primary">
          {value}
        </Typography>
      </Box>
    </Stack>
  </ButtonBase>
);

const FilterOption = ({ active, icon, label, count, onClick }) => (
  <Button
    fullWidth
    onClick={onClick}
    variant="text"
    sx={{
      justifyContent: "flex-start",
      minHeight: 38,
      px: 1,
      color: active ? "primary.main" : "text.secondary",
      bgcolor: active ? "action.selected" : "transparent",
      borderLeft: "2px solid",
      borderColor: active ? "primary.main" : "transparent",
      "&:hover": { bgcolor: "action.hover" },
    }}
  >
    <Box sx={{ display: "grid", placeItems: "center", width: 22, mr: 0.75 }}>
      {icon}
    </Box>
    <Typography variant="body2" sx={{ flex: 1, textAlign: "left" }}>
      {label}
    </Typography>
    <Typography variant="caption" color="text.secondary">
      {count}
    </Typography>
  </Button>
);

export const loader = async () => {
  const loaderQueryClient = new QueryClient();
  logger("prefetching vip list");
  loaderQueryClient.prefetchQuery(vipQueryOptions.list());
  return { dehydratedState: dehydrate(loaderQueryClient) };
};

const VipPageContent = () => {
  const { t } = useTranslation();
  const { openWithId } = usePlayerSidebar();
  const {
    data = [],
    isLoading,
    isFetching,
    refetch,
    dataUpdatedAt,
  } = useQuery(vipQueryOptions.list());

  const [operationMode, setOperationMode] = useState("single");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [durationFilter, setDurationFilter] = useState("all");
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editingVip, setEditingVip] = useState(null);
  const [transferOpen, setTransferOpen] = useState(false);
  const [removeCandidate, setRemoveCandidate] = useState(null);
  const [bulkEditOpen, setBulkEditOpen] = useState(false);
  const [selectedTable, setSelectedTable] = useState(null);
  const [notice, setNotice] = useState(null);
  const forward = operationMode === "multi";

  const rollback = useCallback((context) => {
    if (context?.previousData) {
      queryClient.setQueryData(VIP_QUERY_KEY, context.previousData);
    }
  }, []);

  const { mutate: removeVip, isPending: isRemoving } = useMutation({
    ...vipMutationOptions.remove,
    retry: 0,
    onMutate: async (variables) => {
      await queryClient.cancelQueries({ queryKey: VIP_QUERY_KEY });
      const previousData = queryClient.getQueryData(VIP_QUERY_KEY) || [];
      queryClient.setQueryData(VIP_QUERY_KEY, (current = []) =>
        current.map((row) =>
          row.player_id === variables.player_id
            ? { ...row, _state: "pending" }
            : row
        )
      );
      return { previousData };
    },
    onSuccess: (response, variables, context) => {
      const issue = getMutationIssue(response);
      if (issue) {
        rollback(context);
        setNotice({
          severity: "error",
          text: t("records.vips.partialFailure"),
        });
        return;
      }
      queryClient.setQueryData(VIP_QUERY_KEY, (current = []) =>
        current.filter((row) => row.player_id !== variables.player_id)
      );
      setNotice({ severity: "success", text: t("records.vips.removeSuccess") });
    },
    onError: (_, __, context) => {
      rollback(context);
      setNotice({ severity: "error", text: t("records.vips.removeError") });
    },
  });

  const { mutate: addVip, isPending: isAdding } = useMutation({
    ...vipMutationOptions.add,
    retry: 0,
    onMutate: async (variables) => {
      await queryClient.cancelQueries({ queryKey: VIP_QUERY_KEY });
      const previousData = queryClient.getQueryData(VIP_QUERY_KEY) || [];
      queryClient.setQueryData(VIP_QUERY_KEY, (current = []) => {
        const existing = current.some(
          (row) => row.player_id === variables.player_id
        );
        const optimistic = {
          player_id: variables.player_id,
          name: variables.description,
          vip_expiration: variables.expiration,
          _state: "pending",
        };
        return existing
          ? current.map((row) =>
              row.player_id === variables.player_id
                ? { ...row, ...optimistic }
                : row
            )
          : [optimistic, ...current];
      });
      return { previousData };
    },
    onSuccess: (response, variables, context) => {
      const issue = getMutationIssue(response);
      if (issue) {
        rollback(context);
        setNotice({
          severity: "error",
          text: t("records.vips.partialFailure"),
        });
        return;
      }
      queryClient.setQueryData(VIP_QUERY_KEY, (current = []) =>
        current.map((row) =>
          row.player_id === variables.player_id
            ? { ...row, _state: "completed" }
            : row
        )
      );
      setNotice({ severity: "success", text: t("records.vips.saveSuccess") });
    },
    onError: (_, __, context) => {
      rollback(context);
      setNotice({ severity: "error", text: t("records.vips.saveError") });
    },
  });

  const counts = useMemo(
    () => ({
      total: data.length,
      active: data.filter((vip) => !isVipExpired(vip.vip_expiration)).length,
      expiring: data.filter((vip) => isVipExpiringSoon(vip.vip_expiration))
        .length,
      indefinite: data.filter((vip) => isVipIndefinite(vip.vip_expiration))
        .length,
      expired: data.filter((vip) => isVipExpired(vip.vip_expiration)).length,
    }),
    [data]
  );

  const filteredData = useMemo(() => {
    const normalizedSearch = search.trim().toLocaleLowerCase();
    const durationDays = Number(durationFilter);
    return data.filter((vip) => {
      const category = getVipCategory(vip.vip_expiration);
      const matchesSearch =
        !normalizedSearch ||
        `${vip.name} ${vip.player_id}`
          .toLocaleLowerCase()
          .includes(normalizedSearch);
      const matchesStatus =
        statusFilter === "all" ||
        (statusFilter === "active" && category !== "expired") ||
        category === statusFilter;
      const matchesDuration =
        durationFilter === "all" ||
        (durationFilter === "indefinite" &&
          isVipIndefinite(vip.vip_expiration)) ||
        (Number.isFinite(durationDays) &&
          !isVipIndefinite(vip.vip_expiration) &&
          !isVipExpired(vip.vip_expiration) &&
          !dayjs(vip.vip_expiration).isAfter(dayjs().add(durationDays, "day")));
      return matchesSearch && matchesStatus && matchesDuration;
    });
  }, [data, durationFilter, search, statusFilter]);

  const handleSaveVip = (vip) => {
    addVip({ ...vip, forward });
    setEditorOpen(false);
    setEditingVip(null);
  };

  const handleEdit = useCallback((vip) => {
    setEditingVip(vip);
    setEditorOpen(true);
  }, []);

  const handleRequestRemove = useCallback((vip) => {
    setRemoveCandidate(vip);
  }, []);

  const handleConfirmRemove = () => {
    if (!removeCandidate) return;
    removeVip({ player_id: removeCandidate.player_id, forward });
    setRemoveCandidate(null);
  };

  const handleBulkEditOpen = useCallback((table) => {
    setSelectedTable(table);
    setBulkEditOpen(true);
  }, []);

  const handleBulkEdit = ({ mode, value }) => {
    const selectedRows = selectedTable?.getSelectedRowModel().rows || [];
    selectedRows.forEach(({ original: currentVip }) => {
      let expiration = value;
      if (mode === "extend") {
        if (isVipIndefinite(currentVip.vip_expiration)) {
          expiration = null;
        } else {
          expiration = dayjs(currentVip.vip_expiration).add(
            value.diff(dayjs(), "millisecond")
          );
          if (!expiration.isBefore(dayjs(INDEFINITE_EXPIRATION))) {
            expiration = null;
          }
        }
      }
      addVip({
        player_id: currentVip.player_id,
        description: currentVip.name,
        expiration,
        forward,
      });
    });
    selectedTable?.resetRowSelection();
  };

  const handleBulkRemove = useCallback(
    (table) => {
      table.getSelectedRowModel().rows.forEach(({ original }) => {
        removeVip({ player_id: original.player_id, forward });
      });
      table.resetRowSelection();
    },
    [forward, removeVip]
  );

  const filterRail = (
    <Stack data-theme-surface="panel"
      component="aside"
      aria-label={t("records.vips.filters")}
      sx={{
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.paper",
      }}
    >
      <Box sx={{ px: 1.5, py: 1.25 }}>
        <Typography variant="subtitle2" sx={{ textTransform: "uppercase" }}>
          {t("records.vips.filters")}
        </Typography>
      </Box>
      <Divider />
      <Stack gap={1.5} sx={{ p: 1.5 }}>
        <TextField
          size="small"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder={t("records.vips.search")}
          inputProps={{ "aria-label": t("records.vips.search") }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchOutlinedIcon sx={{ fontSize: 18 }} />
              </InputAdornment>
            ),
          }}
        />

        <Box>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ mb: 0.5, display: "block" }}
          >
            {t("records.vips.status")}
          </Typography>
          <Stack gap={0.25}>
            <FilterOption
              active={statusFilter === "active"}
              icon={
                <PersonOutlineOutlinedIcon
                  sx={{ fontSize: 16, color: "success.main" }}
                />
              }
              label={t("records.vips.active")}
              count={counts.active}
              onClick={() =>
                setStatusFilter(statusFilter === "active" ? "all" : "active")
              }
            />
            <FilterOption
              active={statusFilter === "expiring"}
              icon={
                <ScheduleOutlinedIcon
                  sx={{ fontSize: 16, color: "warning.main" }}
                />
              }
              label={t("records.vips.expiringSoon")}
              count={counts.expiring}
              onClick={() =>
                setStatusFilter(
                  statusFilter === "expiring" ? "all" : "expiring"
                )
              }
            />
            <FilterOption
              active={statusFilter === "indefinite"}
              icon={<AllInclusiveOutlinedIcon sx={{ fontSize: 16 }} />}
              label={t("records.vips.indefinite")}
              count={counts.indefinite}
              onClick={() =>
                setStatusFilter(
                  statusFilter === "indefinite" ? "all" : "indefinite"
                )
              }
            />
            <FilterOption
              active={statusFilter === "expired"}
              icon={
                <ErrorOutlineOutlinedIcon
                  sx={{ fontSize: 16, color: "error.main" }}
                />
              }
              label={t("records.vips.expired")}
              count={counts.expired}
              onClick={() =>
                setStatusFilter(statusFilter === "expired" ? "all" : "expired")
              }
            />
          </Stack>
        </Box>

        <Divider />
        <Box>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ mb: 0.5, display: "block" }}
          >
            {t("records.vips.relativeExpiration")}
          </Typography>
          <FormControl size="small" fullWidth>
            <Select
              value={durationFilter}
              onChange={(event) => setDurationFilter(event.target.value)}
              inputProps={{
                "aria-label": t("records.vips.relativeExpiration"),
              }}
            >
              <MenuItem value="all">{t("records.vips.allDurations")}</MenuItem>
              <MenuItem value="7">
                {t("records.vips.withinDays", { count: 7 })}
              </MenuItem>
              <MenuItem value="30">
                {t("records.vips.withinDays", { count: 30 })}
              </MenuItem>
              <MenuItem value="90">
                {t("records.vips.withinDays", { count: 90 })}
              </MenuItem>
              <MenuItem value="indefinite">
                {t("records.vips.indefinite")}
              </MenuItem>
            </Select>
          </FormControl>
        </Box>

        <Divider />
        <Box>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ mb: 0.5, display: "block" }}
          >
            {t("records.vips.applyChangesTo")}
          </Typography>
          <ToggleButtonGroup
            value={operationMode}
            exclusive
            fullWidth
            size="small"
            onChange={(_, value) => value && setOperationMode(value)}
          >
            <ToggleButton value="single" color="primary">
              {t("records.vips.thisServerShort")}
            </ToggleButton>
            <ToggleButton value="multi" color="primary">
              {t("records.vips.allServersShort")}
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>

        <Button
          variant="outlined"
          startIcon={<RefreshOutlinedIcon />}
          onClick={refetch}
          disabled={isFetching}
        >
          {t("common.refresh")}
        </Button>
      </Stack>
      <Divider />
      <Box sx={{ p: 1.5, bgcolor: "action.hover" }}>
        <Typography variant="caption" color="text.secondary" display="block">
          {t("records.vips.listSource")}
        </Typography>
        <Typography variant="caption" color="primary.main">
          {t("records.vips.currentServerOnly")}
        </Typography>
        <Typography
          variant="caption"
          color="text.secondary"
          display="block"
          sx={{ mt: 0.75 }}
        >
          {isFetching
            ? t("records.vips.updating")
            : dataUpdatedAt
            ? t("records.vips.updatedAt", {
                time: dayjs(dataUpdatedAt).format("HH:mm:ss"),
              })
            : t("records.vips.never")}
        </Typography>
      </Box>
    </Stack>
  );

  const headerActions = (
    <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
      <Button
        variant="contained"
        startIcon={<AddOutlinedIcon />}
        onClick={() => {
          setEditingVip(null);
          setEditorOpen(true);
        }}
      >
        {t("records.vips.addVip")}
      </Button>
      <Button
        variant="outlined"
        startIcon={<ImportExportOutlinedIcon />}
        onClick={() => setTransferOpen(true)}
      >
        {t("records.vips.importExport")}
      </Button>
    </Stack>
  );

  return (
    <>
      <PageHeader
        eyebrow={t("records.vips.eyebrow")}
        title={t("records.vips.title")}
        subtitle={t("records.vips.subtitle")}
        actions={headerActions}
      />

      <Box data-theme-surface="panel"
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr 1fr",
            sm: "repeat(5, minmax(0, 1fr))",
          },
          border: "1px solid",
          borderColor: "divider",
          mb: 1.5,
        }}
        className="wardogs-summary-strip"
      >
        <SummaryItem
          icon={<PeopleAltOutlinedIcon sx={{ fontSize: 20 }} />}
          label={t("records.vips.total")}
          value={counts.total}
          active={statusFilter === "all"}
          onClick={() => setStatusFilter("all")}
          color="text.secondary"
        />
        <SummaryItem
          icon={<PersonOutlineOutlinedIcon sx={{ fontSize: 20 }} />}
          label={t("records.vips.active")}
          value={counts.active}
          active={statusFilter === "active"}
          onClick={() => setStatusFilter("active")}
          color="success.main"
        />
        <SummaryItem
          icon={<ScheduleOutlinedIcon sx={{ fontSize: 20 }} />}
          label={t("records.vips.expiringSoon")}
          value={counts.expiring}
          active={statusFilter === "expiring"}
          onClick={() => setStatusFilter("expiring")}
          color="warning.main"
        />
        <SummaryItem
          icon={<AllInclusiveOutlinedIcon sx={{ fontSize: 20 }} />}
          label={t("records.vips.indefinite")}
          value={counts.indefinite}
          active={statusFilter === "indefinite"}
          onClick={() => setStatusFilter("indefinite")}
          color="text.primary"
        />
        <SummaryItem
          icon={<ErrorOutlineOutlinedIcon sx={{ fontSize: 20 }} />}
          label={t("records.vips.expired")}
          value={counts.expired}
          active={statusFilter === "expired"}
          onClick={() => setStatusFilter("expired")}
          color="error.main"
          wideOnMobile
        />
      </Box>

      {isFetching ? <LinearProgress sx={{ height: 2, mb: 0.5 }} /> : null}

      <Button
        variant="outlined"
        startIcon={<FilterAltOutlinedIcon />}
        onClick={() => setMobileFiltersOpen((current) => !current)}
        sx={{ display: { xs: "inline-flex", md: "none" }, mb: 1 }}
      >
        {mobileFiltersOpen
          ? t("records.vips.hideFilters")
          : t("records.vips.showFilters")}
      </Button>
      <Collapse in={mobileFiltersOpen} sx={{ display: { md: "none" }, mb: 1 }}>
        {filterRail}
      </Collapse>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "264px minmax(0, 1fr)" },
          gap: 1.5,
          alignItems: "start",
        }}
        className="wardogs-vip-workspace"
      >
        <Box sx={{ display: { xs: "none", md: "block" } }}>{filterRail}</Box>
        <VipTable
          data={filteredData}
          totalCount={data.length}
          isLoading={isLoading}
          isFetching={isFetching || isAdding || isRemoving}
          mutationScope={operationMode}
          onEdit={handleEdit}
          onRequestRemove={handleRequestRemove}
          onBulkEdit={handleBulkEditOpen}
          onBulkRemove={handleBulkRemove}
          openProfile={openWithId}
        />
      </Box>

      <VipEditorDialog
        open={editorOpen}
        initialVip={editingVip}
        isSaving={isAdding}
        mutationScope={operationMode}
        onClose={() => {
          setEditorOpen(false);
          setEditingVip(null);
        }}
        onSave={handleSaveVip}
      />
      <VipTransferDialog
        open={transferOpen}
        onClose={() => setTransferOpen(false)}
      />
      <VipBulkEditDialog
        open={bulkEditOpen}
        onClose={() => setBulkEditOpen(false)}
        onConfirm={handleBulkEdit}
        selectedCount={selectedTable?.getSelectedRowModel().rows.length || 0}
      />

      <Dialog
        open={Boolean(removeCandidate)}
        onClose={() => setRemoveCandidate(null)}
        PaperProps={{ sx: { borderRadius: 0 } }}
      >
        <DialogTitle>{t("records.vips.removeTitle")}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {t("records.vips.removeDescription", {
              name: removeCandidate?.name || "",
            })}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRemoveCandidate(null)}>
            {t("common.cancel")}
          </Button>
          <Button
            color="error"
            variant="contained"
            onClick={handleConfirmRemove}
          >
            {t("records.vips.remove")}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={Boolean(notice)}
        autoHideDuration={4500}
        onClose={() => setNotice(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        {notice ? (
          <Alert severity={notice.severity} onClose={() => setNotice(null)}>
            {notice.text}
          </Alert>
        ) : null}
      </Snackbar>
    </>
  );
};

const VipPage = () => {
  const { dehydratedState } = useLoaderData();
  return (
    <HydrationBoundary state={dehydratedState}>
      <VipPageContent />
    </HydrationBoundary>
  );
};

export default VipPage;
