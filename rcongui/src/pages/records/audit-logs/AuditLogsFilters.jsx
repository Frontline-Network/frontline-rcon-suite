import { useEffect, useState } from "react";
import {
  Autocomplete,
  Box,
  Button,
  Chip,
  Collapse,
  Divider,
  Drawer,
  FormControl,
  IconButton,
  InputAdornment,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
  useMediaQuery,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import TuneIcon from "@mui/icons-material/Tune";
import FilterAltOffIcon from "@mui/icons-material/FilterAltOff";
import CloseIcon from "@mui/icons-material/Close";
import { Form, useNavigation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { AUDIT_CATEGORIES } from "./audit-utils";

const shellSx = {
  border: "1px solid",
  borderColor: "divider",
  bgcolor: "background.paper",
  "& .MuiOutlinedInput-root, & .MuiButton-root, & .MuiChip-root": {
    borderRadius: 0,
  },
};
const formId = "audit-log-filter-form";

export default function AuditLogsFilters({
  fields,
  autocompleteOptions,
  category,
  status,
  counts,
  onCategoryChange,
  onStatusChange,
  onSubmit,
  onReset,
}) {
  const { t } = useTranslation();
  const navigation = useNavigation();
  const isMobile = useMediaQuery("(max-width: 599px)");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);
  const [formFields, setFormFields] = useState({
    usernames: fields.usernames || [],
    commands: fields.commands || [],
    parameters: fields.parameters || "",
    time_sort: fields.time_sort || "desc",
    page_size: Number(fields.page_size || 50),
  });

  useEffect(() => {
    setFormFields({
      usernames: fields.usernames || [],
      commands: fields.commands || [],
      parameters: fields.parameters || "",
      time_sort: fields.time_sort || "desc",
      page_size: Number(fields.page_size || 50),
    });
  }, [fields]);

  const update = (name, value) => {
    setFormFields((current) => ({ ...current, [name]: value }));
  };

  const clearAll = () => {
    setFormFields({
      usernames: [],
      commands: [],
      parameters: "",
      time_sort: "desc",
      page_size: 50,
    });
    setAdvancedOpen(false);
    setMobileFiltersOpen(false);
    onCategoryChange("all");
    onStatusChange("all");
    onReset();
  };

  const selectedCategory = AUDIT_CATEGORIES.find(
    (item) => item.id === category
  );
  const hasServerFilters =
    formFields.usernames.length > 0 ||
    formFields.commands.length > 0 ||
    Boolean(formFields.parameters);
  const activeFilterCount = [
    Boolean(formFields.parameters),
    formFields.usernames.length > 0,
    formFields.commands.length > 0,
    category !== "all",
    status !== "all",
    formFields.time_sort !== "desc",
    Number(formFields.page_size) !== 50,
  ].filter(Boolean).length;

  const userControl = (
    <Autocomplete
      multiple
      size="small"
      options={autocompleteOptions.usernames || []}
      value={formFields.usernames}
      onChange={(event, value) => update("usernames", value)}
      limitTags={1}
      filterSelectedOptions
      clearText={t("common.clearSelection")}
      openText={t("common.openOptions")}
      closeText={t("common.closeOptions")}
      noOptionsText={t("common.noResults")}
      renderInput={(params) => (
        <TextField {...params} label={t("records.auditLogs.userFilter")} />
      )}
    />
  );

  const categoryControl = (
    <FormControl size="small" fullWidth>
      <InputLabel id="audit-category-label">
        {t("records.auditLogs.categoryPage")}
      </InputLabel>
      <Select
        labelId="audit-category-label"
        value={category}
        label={t("records.auditLogs.categoryPage")}
        onChange={(event) => onCategoryChange(event.target.value)}
      >
        {AUDIT_CATEGORIES.map((item) => (
          <MenuItem key={item.id} value={item.id}>
            {t(`records.auditLogs.categories.${item.labelKey}`)} (
            {counts[item.id] || 0})
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );

  const statusControl = (
    <FormControl size="small" fullWidth>
      <InputLabel id="audit-status-label">
        {t("records.auditLogs.statusPage")}
      </InputLabel>
      <Select
        labelId="audit-status-label"
        value={status}
        label={t("records.auditLogs.statusPage")}
        onChange={(event) => onStatusChange(event.target.value)}
      >
        {["all", "success", "failed", "partial", "unknown"].map((item) => (
          <MenuItem key={item} value={item}>
            {t(`records.auditLogs.statuses.${item}`)}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );

  const advancedControls = (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: {
          xs: "1fr",
          md: "minmax(260px, 1.5fr) minmax(180px, .7fr) minmax(160px, .6fr)",
        },
        gap: 1,
      }}
    >
      <Autocomplete
        multiple
        size="small"
        options={autocompleteOptions.commands || []}
        value={formFields.commands}
        onChange={(event, value) => update("commands", value)}
        limitTags={2}
        filterSelectedOptions
        clearText={t("common.clearSelection")}
        openText={t("common.openOptions")}
        closeText={t("common.closeOptions")}
        noOptionsText={t("common.noResults")}
        renderInput={(params) => (
          <TextField {...params} label={t("records.auditLogs.commandFilter")} />
        )}
      />

      <FormControl size="small">
        <InputLabel id="audit-sort-label">
          {t("records.auditLogs.sort")}
        </InputLabel>
        <Select
          labelId="audit-sort-label"
          value={formFields.time_sort}
          label={t("records.auditLogs.sort")}
          onChange={(event) => update("time_sort", event.target.value)}
        >
          <MenuItem value="desc">{t("records.auditLogs.newest")}</MenuItem>
          <MenuItem value="asc">{t("records.auditLogs.oldest")}</MenuItem>
        </Select>
      </FormControl>

      <FormControl size="small">
        <InputLabel id="audit-page-size-label">
          {t("records.auditLogs.pageSize")}
        </InputLabel>
        <Select
          labelId="audit-page-size-label"
          value={formFields.page_size}
          label={t("records.auditLogs.pageSize")}
          onChange={(event) => update("page_size", Number(event.target.value))}
        >
          {[25, 50, 100].map((size) => (
            <MenuItem key={size} value={size}>
              {size}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    </Box>
  );

  return (
    <Form id={formId} method="GET" onSubmit={onSubmit}>
      <Box sx={shellSx}>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "minmax(0, 1fr) auto",
              sm: "minmax(240px, 1.4fr) minmax(180px, .8fr)",
              xl: "minmax(300px, 1.5fr) minmax(190px, .8fr) minmax(175px, .7fr) minmax(160px, .65fr) auto auto",
            },
            gap: 1,
            p: 1,
            alignItems: "stretch",
          }}
        >
          <TextField
            size="small"
            name="parameters"
            value={formFields.parameters}
            onChange={(event) => update("parameters", event.target.value)}
            label={t("records.auditLogs.parameters")}
            placeholder={t("records.auditLogs.searchPlaceholder")}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
            }}
          />

          {isMobile ? (
            <Button
              type="button"
              variant="outlined"
              startIcon={<TuneIcon />}
              onClick={() => setMobileFiltersOpen(true)}
              aria-haspopup="dialog"
              sx={{ minWidth: 104, px: 1.5 }}
            >
              {t("records.auditLogs.filter")}
              {activeFilterCount ? ` · ${activeFilterCount}` : ""}
            </Button>
          ) : (
            <>
              {userControl}
              {categoryControl}
              {statusControl}
              <Button
                type="submit"
                variant="contained"
                disabled={navigation.state === "loading"}
                sx={{ minHeight: 40, px: 2.5 }}
              >
                {navigation.state === "loading"
                  ? t("records.auditLogs.filtering")
                  : t("records.auditLogs.filter")}
              </Button>
              <Button
                type="button"
                variant="outlined"
                startIcon={<TuneIcon />}
                onClick={() => setAdvancedOpen((open) => !open)}
                aria-expanded={advancedOpen}
                sx={{ minHeight: 40, px: 2 }}
              >
                {t("records.auditLogs.advanced")}
              </Button>
            </>
          )}
        </Box>

        <Stack
          direction="row"
          alignItems="center"
          spacing={0.75}
          useFlexGap
          flexWrap={isMobile ? "nowrap" : "wrap"}
          sx={{
            minHeight: 42,
            px: 1,
            py: 0.75,
            borderTop: "1px solid",
            borderColor: "divider",
            overflowX: isMobile ? "auto" : "visible",
          }}
        >
          <Chip
            size="small"
            variant="outlined"
            label={`${t("records.auditLogs.category")}: ${t(
              `records.auditLogs.categories.${
                selectedCategory?.labelKey || "all"
              }`
            )}`}
          />
          <Chip
            size="small"
            variant="outlined"
            label={`${t("records.auditLogs.status")}: ${t(
              `records.auditLogs.statuses.${status}`
            )}`}
          />
          {!isMobile &&
            formFields.usernames.map((username) => (
              <Chip
                key={username}
                size="small"
                variant="outlined"
                label={username}
                onDelete={() =>
                  update(
                    "usernames",
                    formFields.usernames.filter((item) => item !== username)
                  )
                }
              />
            ))}
          {!isMobile && formFields.parameters && (
            <Chip
              size="small"
              variant="outlined"
              label={formFields.parameters}
              onDelete={() => update("parameters", "")}
            />
          )}
          <Box sx={{ flexGrow: 1 }} />
          {isMobile ? (
            <IconButton
              size="small"
              color="inherit"
              onClick={clearAll}
              disabled={
                !hasServerFilters && category === "all" && status === "all"
              }
              aria-label={t("records.auditLogs.clearAll")}
              sx={{ color: "text.secondary", flexShrink: 0, borderRadius: 0 }}
            >
              <FilterAltOffIcon fontSize="small" />
            </IconButton>
          ) : (
            <Button
              type="button"
              size="small"
              color="inherit"
              startIcon={<FilterAltOffIcon />}
              onClick={clearAll}
              disabled={
                !hasServerFilters && category === "all" && status === "all"
              }
              sx={{ color: "text.secondary", flexShrink: 0 }}
            >
              {t("records.auditLogs.clearAll")}
            </Button>
          )}
        </Stack>

        {!isMobile && (
          <Collapse in={advancedOpen}>
            <Box
              sx={{
                p: 1,
                borderTop: "1px solid",
                borderColor: "divider",
                bgcolor: "background.default",
              }}
            >
              {advancedControls}
            </Box>
          </Collapse>
        )}

        {formFields.usernames.map((username) => (
          <input
            key={username}
            type="hidden"
            name="usernames"
            value={username}
          />
        ))}
        {formFields.commands.map((command) => (
          <input key={command} type="hidden" name="commands" value={command} />
        ))}
        <input type="hidden" name="time_sort" value={formFields.time_sort} />
        <input type="hidden" name="page_size" value={formFields.page_size} />
      </Box>

      <Drawer
        anchor="bottom"
        open={isMobile && mobileFiltersOpen}
        onClose={() => setMobileFiltersOpen(false)}
        PaperProps={{
          role: "dialog",
          "aria-label": t("records.auditLogs.filter"),
          sx: {
            maxHeight: "92dvh",
            bgcolor: "background.default",
            borderTop: "1px solid",
            borderColor: "divider",
            borderRadius: 0,
          },
        }}
      >
        <Stack
          direction="row"
          alignItems="center"
          sx={{
            px: 1.5,
            minHeight: 52,
            borderBottom: "1px solid",
            borderColor: "divider",
          }}
        >
          <Box>
            <Typography variant="overline" color="primary.main">
              {t("records.auditLogs.eyebrow")}
            </Typography>
            <Typography variant="h6">
              {t("records.auditLogs.filter")}
            </Typography>
          </Box>
          <Box sx={{ flexGrow: 1 }} />
          <IconButton
            onClick={() => setMobileFiltersOpen(false)}
            aria-label={t("common.close")}
            sx={{ borderRadius: 0 }}
          >
            <CloseIcon />
          </IconButton>
        </Stack>
        <Stack spacing={1.25} sx={{ p: 1.5, overflowY: "auto" }}>
          {userControl}
          {categoryControl}
          {statusControl}
          <Divider />
          {advancedControls}
        </Stack>
        <Stack
          direction="row"
          spacing={1}
          sx={{ p: 1.5, borderTop: "1px solid", borderColor: "divider" }}
        >
          <Button variant="outlined" onClick={clearAll} fullWidth>
            {t("records.auditLogs.clearAll")}
          </Button>
          <Button
            type="submit"
            form={formId}
            variant="contained"
            disabled={navigation.state === "loading"}
            onClick={() => setMobileFiltersOpen(false)}
            fullWidth
          >
            {navigation.state === "loading"
              ? t("records.auditLogs.filtering")
              : t("records.auditLogs.filter")}
          </Button>
        </Stack>
      </Drawer>
    </Form>
  );
}
