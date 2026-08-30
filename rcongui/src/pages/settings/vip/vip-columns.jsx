import {
  Box,
  Checkbox,
  CircularProgress,
  IconButton,
  Stack,
  Typography,
} from "@mui/material";
import StarBorderOutlinedIcon from "@mui/icons-material/StarBorderOutlined";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ScheduleOutlinedIcon from "@mui/icons-material/ScheduleOutlined";
import ErrorOutlineOutlinedIcon from "@mui/icons-material/ErrorOutlineOutlined";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import DeleteOutlineOutlinedIcon from "@mui/icons-material/DeleteOutlineOutlined";
import KeyboardArrowDownOutlinedIcon from "@mui/icons-material/KeyboardArrowDownOutlined";
import KeyboardArrowUpOutlinedIcon from "@mui/icons-material/KeyboardArrowUpOutlined";
import dayjs from "dayjs";
import { SortableHeader } from "@/components/table/styles";
import {
  getVipCategory,
  getVipRemainingLabel,
  getVipStatusLabel,
  isVipIndefinite,
} from "./vip-utils";

const StatusCell = ({ expiration, t }) => {
  const category = getVipCategory(expiration);
  const color =
    category === "expired"
      ? "error.main"
      : category === "expiring"
      ? "warning.main"
      : "success.main";
  const Icon =
    category === "expired"
      ? ErrorOutlineOutlinedIcon
      : category === "expiring"
      ? ScheduleOutlinedIcon
      : CheckCircleOutlineIcon;

  return (
    <Stack direction="row" alignItems="center" gap={0.75} sx={{ color }}>
      <Icon sx={{ fontSize: 17 }} />
      <Typography component="span" variant="body2" color="inherit" noWrap>
        {getVipStatusLabel(expiration, t)}
      </Typography>
    </Stack>
  );
};

const getVipColumns = ({
  t,
  isFetching,
  openProfile,
  onEdit,
  onRequestRemove,
}) => [
  {
    id: "select",
    header: ({ table }) => (
      <Checkbox
        checked={table.getIsAllPageRowsSelected()}
        indeterminate={table.getIsSomePageRowsSelected()}
        onChange={table.getToggleAllPageRowsSelectedHandler()}
        inputProps={{ "aria-label": t("records.vips.selectVisible") }}
        size="small"
        sx={{ p: 0 }}
      />
    ),
    cell: ({ row }) => (
      <Checkbox
        checked={row.getIsSelected()}
        disabled={!row.getCanSelect() || isFetching}
        onChange={row.getToggleSelectedHandler()}
        inputProps={{
          "aria-label": t("records.vips.selectPlayer", {
            name: row.original.name,
          }),
        }}
        size="small"
        sx={{ p: 0 }}
      />
    ),
    meta: { variant: "icon" },
    enableSorting: false,
  },
  {
    id: "name",
    accessorKey: "name",
    header: SortableHeader(t("records.vips.player")),
    cell: ({ row }) => (
      <Stack direction="row" alignItems="center" gap={1} minWidth={0}>
        <Box
          aria-hidden="true"
          sx={{
            display: "grid",
            placeItems: "center",
            width: 30,
            height: 30,
            flex: "0 0 30px",
            border: "1px solid",
            borderColor: "divider",
            color: "primary.main",
            bgcolor: "action.hover",
          }}
        >
          <StarBorderOutlinedIcon sx={{ fontSize: 17 }} />
        </Box>
        <Box minWidth={0}>
          <Typography
            component="button"
            type="button"
            variant="body2"
            onClick={() => openProfile(row.original.player_id)}
            sx={{
              display: "block",
              maxWidth: "100%",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              border: 0,
              p: 0,
              bgcolor: "transparent",
              color: "text.primary",
              cursor: "pointer",
              font: "inherit",
              textAlign: "left",
              "&:hover": { color: "primary.main", textDecoration: "underline" },
              "&:focus-visible": {
                outline: "2px solid",
                outlineColor: "primary.main",
                outlineOffset: 2,
              },
            }}
          >
            {row.original.name}
          </Typography>
          <Typography variant="caption" color="text.secondary" noWrap>
            {row.original.player_id}
          </Typography>
        </Box>
      </Stack>
    ),
    meta: { variant: "name" },
  },
  {
    id: "status",
    accessorFn: (row) => getVipCategory(row.vip_expiration),
    header: SortableHeader(t("records.vips.status")),
    cell: ({ row }) => (
      <StatusCell expiration={row.original.vip_expiration} t={t} />
    ),
    meta: { variant: "statusSummary" },
  },
  {
    id: "remaining",
    accessorFn: (row) => {
      if (isVipIndefinite(row.vip_expiration)) return Number.MAX_SAFE_INTEGER;
      return dayjs(row.vip_expiration).valueOf() - dayjs().valueOf();
    },
    header: SortableHeader(t("records.vips.relativeExpiration")),
    cell: ({ row }) => (
      <Typography variant="body2" noWrap>
        {getVipRemainingLabel(row.original.vip_expiration, t)}
      </Typography>
    ),
    meta: { variant: "time" },
  },
  {
    id: "expiration",
    accessorFn: (row) =>
      isVipIndefinite(row.vip_expiration)
        ? Number.MAX_SAFE_INTEGER
        : dayjs(row.vip_expiration).valueOf(),
    header: SortableHeader(t("records.vips.expiration")),
    cell: ({ row }) => (
      <Typography variant="body2" noWrap>
        {isVipIndefinite(row.original.vip_expiration)
          ? t("records.vips.indefinite")
          : dayjs(row.original.vip_expiration).format("LLL")}
      </Typography>
    ),
    meta: { variant: "time" },
  },
  {
    id: "actions",
    header: t("common.actions"),
    enableSorting: false,
    cell: ({ row }) => {
      const state = row.original._state;
      return (
        <Stack
          direction="row"
          justifyContent="flex-end"
          alignItems="center"
          gap={0.25}
        >
          {state === "pending" ? (
            <CircularProgress size={18} aria-label={t("records.vips.saving")} />
          ) : null}
          {state === "error" ? (
            <ErrorOutlineOutlinedIcon color="error" sx={{ fontSize: 18 }} />
          ) : null}
          <IconButton
            size="small"
            aria-label={t("records.vips.editPlayer", {
              name: row.original.name,
            })}
            title={t("records.vips.edit")}
            onClick={() => onEdit(row.original)}
            disabled={isFetching || state === "pending"}
            sx={{ borderRadius: 0 }}
          >
            <EditOutlinedIcon sx={{ fontSize: 18 }} />
          </IconButton>
          <IconButton
            size="small"
            color="error"
            aria-label={t("records.vips.removePlayer", {
              name: row.original.name,
            })}
            title={t("records.vips.remove")}
            onClick={() => onRequestRemove(row.original)}
            disabled={isFetching || state === "pending"}
            sx={{ borderRadius: 0 }}
          >
            <DeleteOutlineOutlinedIcon sx={{ fontSize: 18 }} />
          </IconButton>
          <IconButton
            size="small"
            aria-label={
              row.getIsExpanded()
                ? t("records.vips.collapseDetails", { name: row.original.name })
                : t("records.vips.expandDetails", { name: row.original.name })
            }
            title={
              row.getIsExpanded()
                ? t("records.vips.collapse")
                : t("records.vips.expand")
            }
            onClick={row.getToggleExpandedHandler()}
            sx={{ borderRadius: 0 }}
          >
            {row.getIsExpanded() ? (
              <KeyboardArrowUpOutlinedIcon sx={{ fontSize: 20 }} />
            ) : (
              <KeyboardArrowDownOutlinedIcon sx={{ fontSize: 20 }} />
            )}
          </IconButton>
        </Stack>
      );
    },
    meta: { variant: "action", align: "right" },
  },
];

export default getVipColumns;
export { StatusCell };
