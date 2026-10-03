import {
  Box,
  Chip,
  IconButton,
  Paper,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import DnsOutlinedIcon from "@mui/icons-material/DnsOutlined";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import SyncAltIcon from "@mui/icons-material/SyncAlt";
import { useTranslation } from "react-i18next";

const BlacklistListTile = ({
  blacklist,
  servers,
  selected = false,
  onSelect,
  onEdit,
  onDelete,
}) => {
  const { t } = useTranslation();
  const serverNames =
    blacklist.servers === null
      ? [t("records.blacklists.allServers")]
      : (blacklist.servers || []).map(
          (serverNumber) =>
            servers[serverNumber] ||
            t("records.blacklists.serverNumber", { number: serverNumber })
        );
  const serverSummary = serverNames.length
    ? serverNames.join(", ")
    : t("records.blacklists.noServers");
  const syncLabel = t(
    `records.blacklists.syncMethods.${blacklist.sync}`,
    blacklist.sync || t("common.unknown")
  );

  const select = () => onSelect?.(blacklist);

  return (
    <Paper
      variant="outlined"
      sx={{
        borderRadius: 0,
        borderColor: selected ? "primary.main" : "divider",
        borderLeftWidth: selected ? 3 : 1,
        bgcolor: selected ? "action.selected" : "background.paper",
        overflow: "hidden",
      }}
    >
      <Box
        role="button"
        tabIndex={0}
        aria-pressed={selected}
        onClick={select}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            select();
          }
        }}
        sx={(theme) => ({
          cursor: "pointer",
          p: 1.5,
          "&:hover": { bgcolor: "action.hover" },
          "&:focus-visible": {
            outline: `2px solid ${theme.palette.primary.main}`,
            outlineOffset: -2,
          },
        })}
      >
        <Stack direction="row" alignItems="flex-start" spacing={1.25}>
          <Box data-theme-surface="control"
            sx={{
              width: 34,
              height: 34,
              flex: "0 0 auto",
              display: "grid",
              placeItems: "center",
              border: "1px solid",
              borderColor: selected ? "primary.main" : "divider",
              color: selected ? "primary.main" : "text.secondary",
            }}
          >
            <Typography variant="caption" fontWeight={800}>
              #{blacklist.id}
            </Typography>
          </Box>
          <Box sx={{ minWidth: 0, flex: 1 }}>
            <Typography sx={{ fontWeight: 700 }} noWrap>
              {blacklist.name}
            </Typography>
            <Stack
              direction="row"
              spacing={1.25}
              alignItems="center"
              sx={{ mt: 0.65, minWidth: 0 }}
            >
              <Stack
                direction="row"
                spacing={0.5}
                alignItems="center"
                sx={{ minWidth: 0 }}
              >
                <DnsOutlinedIcon sx={{ fontSize: 16 }} color="disabled" />
                <Typography variant="caption" color="text.secondary" noWrap>
                  {serverSummary}
                </Typography>
              </Stack>
              <Stack direction="row" spacing={0.5} alignItems="center">
                <SyncAltIcon sx={{ fontSize: 16 }} color="disabled" />
                <Typography variant="caption" color="text.secondary" noWrap>
                  {syncLabel}
                </Typography>
              </Stack>
            </Stack>
          </Box>
        </Stack>
      </Box>

      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        sx={{ borderTop: "1px solid", borderColor: "divider", pl: 1.5 }}
      >
        <Chip
          size="small"
          variant="outlined"
          label={
            blacklist.servers === null
              ? t("records.blacklists.globalScope")
              : t("records.blacklists.serverScope", {
                  count: blacklist.servers?.length || 0,
                })
          }
          sx={{ borderRadius: 0 }}
        />
        <Stack direction="row">
          <Tooltip title={t("common.edit")}>
            <IconButton
              onClick={() => onEdit(blacklist)}
              aria-label={t("records.blacklists.editListNamed", {
                name: blacklist.name,
              })}
              sx={{ borderRadius: 0, width: 44, height: 44 }}
            >
              <EditOutlinedIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title={t("common.delete")}>
            <span>
              <IconButton
                onClick={() => onDelete(blacklist)}
                disabled={blacklist.id === 0}
                aria-label={t("records.blacklists.deleteListNamed", {
                  name: blacklist.name,
                })}
                sx={{ borderRadius: 0, width: 44, height: 44 }}
              >
                <DeleteOutlineIcon />
              </IconButton>
            </span>
          </Tooltip>
        </Stack>
      </Stack>
    </Paper>
  );
};

export default BlacklistListTile;
