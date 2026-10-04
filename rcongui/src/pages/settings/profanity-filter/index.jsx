import { useEffect, useMemo, useState } from "react";
import {
  Box,
  Button,
  Checkbox,
  IconButton,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Stack,
  TextField,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteIcon from "@mui/icons-material/Delete";
import DownloadIcon from "@mui/icons-material/Download";
import { FixedSizeList } from "react-window";
import { useLoaderData, useSubmit } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { cmd } from "@/utils/fetchUtils";
import { SearchInput } from "@/components/shared/SearchInput";
import { InputFileUpload } from "@/components/shared/InputFileUpload";
import ConfirmButton from "@/components/shared/ConfirmButton";
import PageHeader from "@/components/shared/PageHeader";
import exportFile from "@/utils/exportFile";
import { isFakeMode } from "@/mirage/demo-data";

const INTENT = {
  SINGLE: 0,
  ALL: 1,
};

const normalizeWords = (words) => [
  ...new Set(words.map((word) => word.trim()).filter(Boolean)),
];

const listsMatch = (left, right) =>
  left.length === right.length &&
  left.every((word, index) => word === right[index]);

function SummaryMetric({ label, value, tone = "text.primary" }) {
  return (
    <Box sx={{ minWidth: 0, px: { xs: 1.5, md: 2 }, py: 1.25 }}>
      <Typography
        variant="overline"
        color="text.secondary"
        sx={{ display: "block", lineHeight: 1.2 }}
      >
        {label}
      </Typography>
      <Typography variant="h6" color={tone} sx={{ mt: 0.5, lineHeight: 1 }}>
        {value}
      </Typography>
    </Box>
  );
}

export const loader = async () => {
  const profanities = isFakeMode()
    ? ["beleidigung-demo", "spam-demo"]
    : await cmd.GET_PROFANITIES();
  return { profanities };
};

export const action = async ({ request }) => {
  const { profanities, ...rest } = Object.fromEntries(await request.formData());
  const payload = {
    profanities: profanities.length ? profanities.split(",") : [],
    ...rest,
  };
  return cmd.SET_PROFANITIES({ payload });
};

const ProfanityFilter = () => {
  const { t } = useTranslation();
  const { profanities: serverProfanities } = useLoaderData();
  const [profanities, setProfanities] = useState(serverProfanities);
  const [checked, setChecked] = useState([]);
  const [searched, setSearched] = useState("");
  const [newProfanity, setNewProfanity] = useState("");
  const submit = useSubmit();
  const theme = useTheme();
  const compact = useMediaQuery(theme.breakpoints.down("md"));

  const filteredProfanities = useMemo(() => {
    const query = searched.trim().toLocaleLowerCase();
    if (!query) return profanities;
    return profanities.filter((word) =>
      word.toLocaleLowerCase().includes(query)
    );
  }, [profanities, searched]);

  const normalizedServerProfanities = useMemo(
    () => normalizeWords(serverProfanities),
    [serverProfanities]
  );
  const selectedVisible = useMemo(
    () => filteredProfanities.filter((word) => checked.includes(word)),
    [checked, filteredProfanities]
  );
  const hasChanges = !listsMatch(profanities, normalizedServerProfanities);
  const normalizedNewProfanity = newProfanity.trim();
  const duplicateEntry = profanities.includes(normalizedNewProfanity);
  const allVisibleSelected =
    filteredProfanities.length > 0 &&
    selectedVisible.length === filteredProfanities.length;

  const handleToggle = (value) => () => {
    setChecked((current) =>
      current.includes(value)
        ? current.filter((entry) => entry !== value)
        : [...current, value]
    );
  };

  const handleAddProfanity = () => {
    if (!normalizedNewProfanity || duplicateEntry) return;
    setProfanities((current) => [normalizedNewProfanity, ...current]);
    setNewProfanity("");
  };

  const handleDeleteSingleProfanity = (word) => {
    setProfanities((current) => current.filter((entry) => entry !== word));
    setChecked((current) => current.filter((entry) => entry !== word));
  };

  const handleDeleteSelectedProfanities = () => {
    setProfanities((current) =>
      current.filter((word) => !checked.includes(word))
    );
    setChecked([]);
  };

  const handleToggleSelectAll = (event) => {
    if (event.target.checked) {
      setChecked((current) => [
        ...new Set([...current, ...filteredProfanities]),
      ]);
      return;
    }
    setChecked((current) =>
      current.filter((word) => !filteredProfanities.includes(word))
    );
  };

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (loadEvent) => {
      setProfanities(
        normalizeWords(String(loadEvent.target.result).split(/\r?\n/))
      );
      setChecked([]);
    };
    reader.readAsText(file);
    event.target.value = "";
  };

  const submitChanges = (intent) => () => {
    const formData = new FormData();
    formData.append("profanities", profanities);
    if (intent === INTENT.ALL) formData.append("forward", true);
    submit(formData, { method: "POST" });
  };

  useEffect(() => {
    setProfanities(normalizeWords(serverProfanities));
    setChecked([]);
  }, [serverProfanities]);

  return (
    <Box
      sx={{
        maxWidth: (currentTheme) => currentTheme.breakpoints.values.lg,
        minWidth: 0,
        pb: { xs: 10, md: 0 },
      }}
    >
      <PageHeader
        eyebrow={t("settings.profanity.eyebrow")}
        title={t("settings.profanity.title")}
        subtitle={t("settings.profanity.subtitle")}
      />

      <Box data-theme-surface="panel"
        component="section"
        aria-label={t("settings.profanity.summary")}
        className="wardogs-summary-strip"
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
          mb: 1.5,
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.paper",
          "& > *:not(:last-child)": {
            borderRight: "1px solid",
            borderColor: "divider",
          },
        }}
      >
        <SummaryMetric
          label={t("settings.profanity.totalTerms")}
          value={profanities.length}
        />
        <SummaryMetric
          label={t("settings.profanity.selectedTerms")}
          value={checked.length}
          tone={checked.length ? "primary.main" : "text.primary"}
        />
        <SummaryMetric
          label={t("settings.profanity.changeStatus")}
          value={t(
            hasChanges
              ? "settings.profanity.unsaved"
              : "settings.profanity.saved"
          )}
          tone={hasChanges ? "warning.main" : "success.main"}
        />
      </Box>

      <Box data-theme-surface="panel"
        component="section"
        aria-label={t("settings.profanity.workbench")}
        className="wardogs-profanity-workspace"
        sx={{
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.paper",
        }}
      >
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "320px minmax(0, 1fr)" },
            minWidth: 0,
          }}
        >
          <Stack
            component="aside"
            spacing={2}
            sx={{
              p: 2,
              borderRight: { md: "1px solid" },
              borderBottom: { xs: "1px solid", md: 0 },
              borderColor: "divider",
              bgcolor: "background.default",
            }}
          >
            <Box>
              <Typography variant="h6">
                {t("settings.profanity.addSection")}
              </Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mt: 0.5 }}
              >
                {t("settings.profanity.addDescription")}
              </Typography>
            </Box>

            <Stack spacing={1}>
              <TextField
                autoComplete="off"
                value={newProfanity}
                onChange={(event) => setNewProfanity(event.target.value)}
                onKeyDown={(event) =>
                  event.key === "Enter" && handleAddProfanity()
                }
                fullWidth
                label={t("settings.profanity.newEntry")}
                error={duplicateEntry}
                helperText={
                  duplicateEntry
                    ? t("settings.profanity.duplicateEntry")
                    : t("settings.profanity.entryHint")
                }
              />
              <Button
                onClick={handleAddProfanity}
                variant="contained"
                startIcon={<AddIcon />}
                disabled={!normalizedNewProfanity || duplicateEntry}
                sx={{ minHeight: 44 }}
              >
                {t("settings.profanity.add")}
              </Button>
            </Stack>

            <Box sx={{ borderTop: "1px solid", borderColor: "divider", pt: 2 }}>
              <Typography variant="overline" color="text.secondary">
                {t("settings.profanity.fileTools")}
              </Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mt: 0.5 }}
              >
                {t("settings.profanity.fileToolsDescription")}
              </Typography>
            </Box>

            <Stack
              direction={{ xs: "column", sm: "row", md: "column" }}
              spacing={1}
            >
              <InputFileUpload
                text={t("settings.profanity.upload")}
                color="secondary"
                variant="outlined"
                onChange={handleFileUpload}
                accept=".txt"
                sx={{ minHeight: 44, flex: 1 }}
              />
              <Button
                onClick={() => exportFile(profanities, "profanities")}
                variant="outlined"
                color="secondary"
                startIcon={<DownloadIcon />}
                sx={{ minHeight: 44, flex: 1 }}
              >
                {t("settings.profanity.download")}
              </Button>
            </Stack>
          </Stack>

          <Box sx={{ minWidth: 0 }}>
            <Stack
              direction={{ xs: "column", sm: "row" }}
              alignItems={{ xs: "stretch", sm: "center" }}
              justifyContent="space-between"
              gap={1.5}
              sx={{ p: 2, borderBottom: "1px solid", borderColor: "divider" }}
            >
              <Box>
                <Typography variant="h6">
                  {t("settings.profanity.listSection")}
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mt: 0.5 }}
                >
                  {t("settings.profanity.listDescription", {
                    visible: filteredProfanities.length,
                    total: profanities.length,
                  })}
                </Typography>
              </Box>
              <SearchInput
                value={searched}
                onChange={(event) => setSearched(event.target.value)}
                placeholder={t("settings.profanity.search")}
                sx={{ width: { xs: "100%", sm: 280 } }}
              />
            </Stack>

            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: "44px minmax(0, 1fr) auto",
                alignItems: "center",
                minHeight: 52,
                px: 1.5,
                py: 0.5,
                borderBottom: "1px solid",
                borderColor: "divider",
              }}
            >
              <Checkbox
                checked={allVisibleSelected}
                indeterminate={
                  selectedVisible.length > 0 && !allVisibleSelected
                }
                size="small"
                onChange={handleToggleSelectAll}
                inputProps={{
                  "aria-label": t("settings.profanity.selectVisible"),
                }}
                sx={{ justifySelf: "center" }}
              />
              <Typography variant="subtitle2" sx={{ pl: 1 }}>
                {t("settings.profanity.selectVisible")}
              </Typography>
              <Button
                onClick={handleDeleteSelectedProfanities}
                color="error"
                variant="outlined"
                startIcon={<DeleteIcon />}
                disabled={!checked.length}
                sx={{ minHeight: 40, justifySelf: "end" }}
              >
                {t("settings.profanity.deleteSelectedWithCount", {
                  count: checked.length,
                })}
              </Button>
            </Box>

            {filteredProfanities.length ? (
              <FixedSizeList
                height={compact ? 410 : 480}
                itemSize={compact ? 56 : 48}
                itemCount={filteredProfanities.length}
                itemData={filteredProfanities}
                itemKey={(index, data) => data[index]}
                overscanCount={8}
                width="100%"
              >
                {({ index, style }) => {
                  const word = filteredProfanities[index];
                  const selected = checked.includes(word);
                  const labelId = `profanity-label-${index}`;
                  return (
                    <ListItem
                      style={style}
                      disablePadding
                      sx={{
                        borderBottom: "1px solid",
                        borderColor: "divider",
                        bgcolor: selected ? "action.selected" : "transparent",
                        "& .MuiListItemSecondaryAction-root": { right: 12 },
                      }}
                      secondaryAction={
                        <IconButton
                          aria-label={`${t("common.delete")} ${word}`}
                          onClick={() => handleDeleteSingleProfanity(word)}
                          color="error"
                          sx={{ minWidth: 44, minHeight: 44 }}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      }
                    >
                      <ListItemButton
                        role={undefined}
                        onClick={handleToggle(word)}
                        sx={{ minHeight: "100%", px: 1.5, pr: 8 }}
                      >
                        <ListItemIcon
                          sx={{
                            width: 44,
                            minWidth: 44,
                            justifyContent: "center",
                          }}
                        >
                          <Checkbox
                            size="small"
                            checked={selected}
                            tabIndex={-1}
                            disableRipple
                            inputProps={{ "aria-labelledby": labelId }}
                          />
                        </ListItemIcon>
                        <ListItemText
                          id={labelId}
                          primary={word}
                          primaryTypographyProps={{
                            fontFamily: "monospace",
                            fontWeight: selected ? 700 : 500,
                          }}
                        />
                      </ListItemButton>
                    </ListItem>
                  );
                }}
              </FixedSizeList>
            ) : (
              <Box
                sx={{
                  minHeight: 260,
                  display: "grid",
                  placeItems: "center",
                  p: 3,
                  textAlign: "center",
                }}
              >
                <Box>
                  <Typography variant="h6">
                    {t("settings.profanity.noMatches")}
                  </Typography>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mt: 0.5 }}
                  >
                    {t("settings.profanity.noMatchesDescription")}
                  </Typography>
                </Box>
              </Box>
            )}
          </Box>
        </Box>

        <Stack
          direction={{ xs: "column", sm: "row" }}
          alignItems={{ xs: "stretch", sm: "center" }}
          justifyContent="space-between"
          gap={1.5}
          sx={{
            position: "sticky",
            bottom: 0,
            zIndex: 2,
            px: 2,
            py: 1.5,
            borderTop: "1px solid",
            borderColor: "divider",
            bgcolor: "background.paper",
            boxShadow: "0 -8px 24px rgba(0, 0, 0, 0.16)",
          }}
        >
          <Box role="status" aria-live="polite">
            <Typography
              variant="subtitle2"
              color={hasChanges ? "warning.main" : "success.main"}
            >
              {t(
                hasChanges
                  ? "settings.profanity.changesPending"
                  : "settings.profanity.noChanges"
              )}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {t("settings.profanity.publishHint")}
            </Typography>
          </Box>

          <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
            <Button
              variant="contained"
              onClick={submitChanges(INTENT.SINGLE)}
              disabled={!hasChanges}
              sx={{ minHeight: 44 }}
            >
              {t("settings.profanity.applyCurrentServer")}
            </Button>
            <ConfirmButton
              onConfirm={submitChanges(INTENT.ALL)}
              title={t("settings.profanity.applyAllTitle")}
              description={t("settings.profanity.applyAllDescription")}
              buttonText={t("settings.profanity.applyAllServers")}
              disabled={!hasChanges}
              buttonProps={{
                variant: "outlined",
                sx: { minHeight: 44, whiteSpace: "nowrap" },
              }}
            />
          </Stack>
        </Stack>
      </Box>
    </Box>
  );
};

export default ProfanityFilter;
