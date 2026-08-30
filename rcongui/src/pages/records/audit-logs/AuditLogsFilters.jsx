import { useEffect, useState } from "react";
import {
  Autocomplete,
  Box,
  Button,
  Chip,
  Collapse,
  FormControl,
  InputAdornment,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import TuneIcon from "@mui/icons-material/Tune";
import FilterAltOffIcon from "@mui/icons-material/FilterAltOff";
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
  const [advancedOpen, setAdvancedOpen] = useState(false);
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

  return (
    <Form method="GET" onSubmit={onSubmit}>
      <Box sx={shellSx}>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
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
            placeholder={t("records.auditLogs.searchPlaceholder")}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
            }}
          />

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
              <TextField
                {...params}
                label={t("records.auditLogs.userFilter")}
              />
            )}
          />

          <FormControl size="small">
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

          <FormControl size="small">
            <InputLabel id="audit-status-label">
              {t("records.auditLogs.statusPage")}
            </InputLabel>
            <Select
              labelId="audit-status-label"
              value={status}
              label={t("records.auditLogs.statusPage")}
              onChange={(event) => onStatusChange(event.target.value)}
            >
              <MenuItem value="all">
                {t("records.auditLogs.statuses.all")}
              </MenuItem>
              <MenuItem value="success">
                {t("records.auditLogs.statuses.success")}
              </MenuItem>
              <MenuItem value="failed">
                {t("records.auditLogs.statuses.failed")}
              </MenuItem>
              <MenuItem value="partial">
                {t("records.auditLogs.statuses.partial")}
              </MenuItem>
              <MenuItem value="unknown">
                {t("records.auditLogs.statuses.unknown")}
              </MenuItem>
            </Select>
          </FormControl>

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
        </Box>

        <Stack
          direction="row"
          alignItems="center"
          spacing={0.75}
          useFlexGap
          flexWrap="wrap"
          sx={{
            minHeight: 42,
            px: 1,
            py: 0.75,
            borderTop: "1px solid",
            borderColor: "divider",
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
          {formFields.usernames.map((username) => (
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
          {formFields.parameters && (
            <Chip
              size="small"
              variant="outlined"
              label={formFields.parameters}
              onDelete={() => update("parameters", "")}
            />
          )}
          <Box sx={{ flexGrow: 1 }} />
          <Button
            type="button"
            size="small"
            color="inherit"
            startIcon={<FilterAltOffIcon />}
            onClick={clearAll}
            disabled={
              !hasServerFilters && category === "all" && status === "all"
            }
            sx={{ color: "text.secondary" }}
          >
            {t("records.auditLogs.clearAll")}
          </Button>
        </Stack>

        <Collapse in={advancedOpen}>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                md: "minmax(260px, 1.5fr) minmax(180px, .7fr) minmax(160px, .6fr)",
              },
              gap: 1,
              p: 1,
              borderTop: "1px solid",
              borderColor: "divider",
              bgcolor: "background.default",
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
                <TextField
                  {...params}
                  label={t("records.auditLogs.commandFilter")}
                />
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
                <MenuItem value="desc">
                  {t("records.auditLogs.newest")}
                </MenuItem>
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
                onChange={(event) =>
                  update("page_size", Number(event.target.value))
                }
              >
                {[25, 50, 100].map((size) => (
                  <MenuItem key={size} value={size}>
                    {size}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        </Collapse>

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
    </Form>
  );
}
