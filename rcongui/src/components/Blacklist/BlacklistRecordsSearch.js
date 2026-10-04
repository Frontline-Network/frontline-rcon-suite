import {
  Box,
  Button,
  FormControl,
  InputAdornment,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import TagIcon from "@mui/icons-material/Tag";
import ReplayIcon from "@mui/icons-material/Replay";
import RadioButtonCheckedIcon from "@mui/icons-material/RadioButtonChecked";
import RadioButtonUncheckedIcon from "@mui/icons-material/RadioButtonUnchecked";
import { useState } from "react";
import { useTranslation } from "react-i18next";

const STATUS_OPTIONS = ["active", "all", "expired"];

const StatusButton = ({ active, children, onClick }) => (
  <Button
    type="button"
    onClick={onClick}
    aria-pressed={active}
    startIcon={
      active ? (
        <RadioButtonCheckedIcon fontSize="small" />
      ) : (
        <RadioButtonUncheckedIcon fontSize="small" />
      )
    }
    sx={{
      justifyContent: "flex-start",
      minHeight: 40,
      px: 1.25,
      borderRadius: 0,
      border: "1px solid",
      borderColor: active ? "primary.dark" : "divider",
      color: active ? "text.primary" : "text.secondary",
      bgcolor: active ? "action.selected" : "transparent",
      "& + &": { borderTop: 0 },
      "& .MuiButton-startIcon": {
        color: active ? "primary.main" : "text.disabled",
      },
    }}
  >
    {children}
  </Button>
);

const BlacklistRecordsSearch = ({
  blacklists,
  onSearch,
  disabled,
  totalRecords = 0,
}) => {
  const { t } = useTranslation();
  const [playerIdQuery, setPlayerIdQuery] = useState("");
  const [reasonQuery, setReasonQuery] = useState("");
  const [blacklistQuery, setBlacklistQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [pageSize, setPageSize] = useState(50);

  const submitSearch = (event) => {
    event?.preventDefault();
    onSearch({
      player_id: playerIdQuery.trim(),
      reason: reasonQuery.trim(),
      blacklist_id: blacklistQuery === "" ? null : blacklistQuery,
      exclude_expired: status === "active",
      expired_only: status === "expired",
      page_size: pageSize,
    });
  };

  const reset = () => {
    setPlayerIdQuery("");
    setReasonQuery("");
    setBlacklistQuery("");
    setStatus("all");
    setPageSize(50);
    onSearch({
      player_id: "",
      reason: "",
      blacklist_id: null,
      exclude_expired: false,
      expired_only: false,
      page_size: 50,
    });
  };

  return (
    <Box data-theme-surface="panel"
      component="form"
      className="wardogs-blacklist-filters"
      onSubmit={submitSearch}
      sx={{
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.paper",
        p: 1.5,
        position: { lg: "sticky" },
        top: { lg: 68 },
      }}
    >
      <Typography
        component="h2"
        variant="subtitle2"
        sx={{
          mb: 1.25,
          textTransform: "uppercase",
          letterSpacing: "0.09em",
          fontWeight: 700,
        }}
      >
        {t("records.blacklists.filters")}
      </Typography>

      <Stack gap={1} className="wardogs-blacklist-filter-fields">
        <TextField
          fullWidth
          size="small"
          label={t("records.blacklists.searchNameReasonShort")}
          value={reasonQuery}
          onChange={(event) => setReasonQuery(event.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
        />
        <TextField
          fullWidth
          size="small"
          label={t("records.blacklists.playerId")}
          value={playerIdQuery}
          onChange={(event) => setPlayerIdQuery(event.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <TagIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
        />
        <FormControl fullWidth size="small">
          <InputLabel id="blacklist-filter-list-label">
            {t("records.blacklists.list")}
          </InputLabel>
          <Select
            labelId="blacklist-filter-list-label"
            value={blacklistQuery}
            label={t("records.blacklists.list")}
            onChange={(event) => setBlacklistQuery(event.target.value)}
          >
            <MenuItem value="">{t("records.blacklists.allLists")}</MenuItem>
            {blacklists.map((blacklist) => (
              <MenuItem key={blacklist.id} value={blacklist.id}>
                {blacklist.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ mt: 0.75, textTransform: "uppercase", letterSpacing: "0.08em" }}
        >
          {t("records.blacklists.status")}
        </Typography>
        <Stack gap={0}>
          {STATUS_OPTIONS.map((option) => (
            <StatusButton
              key={option}
              active={status === option}
              onClick={() => setStatus(option)}
            >
              {t(`records.blacklists.statusOptions.${option}`)}
            </StatusButton>
          ))}
        </Stack>

        <Button
          type="submit"
          disabled={disabled}
          variant="contained"
          color="primary"
          startIcon={<SearchIcon />}
          sx={{ mt: 1, minHeight: 42, borderRadius: 0 }}
        >
          {t("common.search")}
        </Button>
        <Button
          type="button"
          disabled={disabled}
          variant="outlined"
          color="inherit"
          startIcon={<ReplayIcon />}
          onClick={reset}
          sx={{ minHeight: 40, borderRadius: 0 }}
        >
          {t("common.reset")}
        </Button>

        <Typography
          sx={{ mt: 1, fontWeight: 600, fontVariantNumeric: "tabular-nums" }}
        >
          {t("records.blacklists.recordsCount", { count: totalRecords })}
        </Typography>
        <FormControl fullWidth size="small">
          <InputLabel id="blacklist-filter-page-size-label">
            {t("common.pagination.pageSize")}
          </InputLabel>
          <Select
            labelId="blacklist-filter-page-size-label"
            value={pageSize}
            label={t("common.pagination.pageSize")}
            onChange={(event) => setPageSize(Number(event.target.value))}
          >
            {[10, 20, 50, 100, 200].map((size) => (
              <MenuItem key={size} value={size}>
                {t("common.pagination.show", { count: size })}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Stack>
    </Box>
  );
};

export default BlacklistRecordsSearch;
