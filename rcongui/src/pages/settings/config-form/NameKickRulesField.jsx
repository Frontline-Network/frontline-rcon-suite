import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  IconButton,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import AddOutlinedIcon from "@mui/icons-material/AddOutlined";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import ScienceOutlinedIcon from "@mui/icons-material/ScienceOutlined";
import { useTranslation } from "react-i18next";

export const NAME_KICK_PRESETS = [
  {
    id: "unreadable",
    pattern: String.raw`(^[^a-zA-Z0-9äöüÄÖÜß\[\]]+$)`,
    tone: "success",
  },
  {
    id: "blank",
    pattern: String.raw`^\s*$`,
    tone: "info",
  },
  {
    id: "strictCharacters",
    pattern: String.raw`^.*[^a-zA-Z0-9äöüÄÖÜß _.\-\[\]].*$`,
    tone: "warning",
  },
];

const compilePythonMatchPreview = (expression) => {
  let source = String(expression || "");
  let flags = "";
  const inlineFlags = source.match(/^\(\?([ims]+)\)/);
  if (inlineFlags) {
    flags = inlineFlags[1];
    source = source.slice(inlineFlags[0].length);
  }

  // Python's re.match always starts at the beginning of the player name.
  // JavaScript RegExp#test searches unless the expression is anchored.
  if (!source.startsWith("^")) source = `^(?:${source})`;
  return new RegExp(source, flags);
};

const previewPatterns = (patterns, playerName) =>
  patterns.reduce(
    (result, pattern, index) => {
      try {
        if (compilePythonMatchPreview(pattern).test(playerName)) {
          result.matches.push({ pattern, index });
        }
      } catch {
        result.unsupported.push({ pattern, index });
      }
      return result;
    },
    { matches: [], unsupported: [] }
  );

export default function NameKickRulesField({
  value = [],
  disabled = false,
  onChange,
}) {
  const { t } = useTranslation();
  const [customPattern, setCustomPattern] = useState("");
  const [testName, setTestName] = useState("");
  const patterns = Array.isArray(value) ? value : [];
  const preview = useMemo(
    () => previewPatterns(patterns, testName),
    [patterns, testName]
  );

  const togglePreset = (preset) => {
    if (patterns.includes(preset.pattern)) {
      onChange(patterns.filter((pattern) => pattern !== preset.pattern));
      return;
    }
    onChange([...patterns, preset.pattern]);
  };

  const updatePattern = (index, nextPattern) => {
    const nextPatterns = [...patterns];
    nextPatterns[index] = nextPattern;
    onChange(nextPatterns);
  };

  const addCustomPattern = () => {
    const nextPattern = customPattern.trim();
    if (!nextPattern || patterns.includes(nextPattern)) return;
    onChange([...patterns, nextPattern]);
    setCustomPattern("");
  };

  return (
    <Stack spacing={3} data-testid="name-kick-rules-editor">
      <Alert severity="info">
        <Typography variant="body2" fontWeight={850}>
          {t("settings.configForms.nameKicks.rulesEditor.noticeTitle")}
        </Typography>
        <Typography variant="body2">
          {t("settings.configForms.nameKicks.rulesEditor.noticeBody")}
        </Typography>
      </Alert>

      <Box>
        <Typography variant="overline" fontWeight={850}>
          {t("settings.configForms.nameKicks.rulesEditor.templatesTitle")}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          {t("settings.configForms.nameKicks.rulesEditor.templatesHelp")}
        </Typography>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              md: "repeat(3, minmax(0, 1fr))",
            },
            gap: 1.25,
          }}
        >
          {NAME_KICK_PRESETS.map((preset) => {
            const active = patterns.includes(preset.pattern);
            return (
              <Box data-theme-surface="panel"
                key={preset.id}
                sx={{
                  p: 1.5,
                  minHeight: 178,
                  display: "flex",
                  flexDirection: "column",
                  border: "1px solid",
                  borderColor: active ? "primary.main" : "divider",
                  bgcolor: active
                    ? "rgba(214, 170, 77, 0.08)"
                    : "background.default",
                  borderRadius: 0,
                }}
              >
                <Stack
                  direction="row"
                  alignItems="center"
                  justifyContent="space-between"
                  spacing={1}
                >
                  <Typography variant="body2" fontWeight={900}>
                    {t(
                      `settings.configForms.nameKicks.rulesEditor.presets.${preset.id}.title`
                    )}
                  </Typography>
                  {active && (
                    <Chip
                      size="small"
                      color={preset.tone}
                      icon={<CheckCircleOutlineIcon />}
                      label={t(
                        "settings.configForms.nameKicks.rulesEditor.active"
                      )}
                    />
                  )}
                </Stack>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ mt: 0.75, mb: 1.5 }}
                >
                  {t(
                    `settings.configForms.nameKicks.rulesEditor.presets.${preset.id}.description`
                  )}
                </Typography>
                <Button
                  size="small"
                  variant={active ? "outlined" : "contained"}
                  color={active ? "inherit" : "primary"}
                  disabled={disabled}
                  aria-pressed={active}
                  data-testid={`name-kick-preset-${preset.id}`}
                  onClick={() => togglePreset(preset)}
                  sx={{ mt: "auto" }}
                >
                  {t(
                    active
                      ? "settings.configForms.nameKicks.rulesEditor.removeTemplate"
                      : "settings.configForms.nameKicks.rulesEditor.useTemplate"
                  )}
                </Button>
              </Box>
            );
          })}
        </Box>
      </Box>

      <Box>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          justifyContent="space-between"
          alignItems={{ xs: "flex-start", sm: "center" }}
          spacing={0.5}
          sx={{ mb: 1.25 }}
        >
          <Box>
            <Typography variant="overline" fontWeight={850}>
              {t("settings.configForms.nameKicks.rulesEditor.configuredTitle")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t("settings.configForms.nameKicks.rulesEditor.configuredHelp")}
            </Typography>
          </Box>
          <Chip
            size="small"
            label={t("settings.configForms.nameKicks.rulesEditor.ruleCount", {
              count: patterns.length,
            })}
          />
        </Stack>

        {patterns.length === 0 ? (
          <Alert severity="warning">
            {t("settings.configForms.nameKicks.rulesEditor.noRules")}
          </Alert>
        ) : (
          <Stack spacing={1}>
            {patterns.map((pattern, index) => (
              <Stack
                key={index}
                direction="row"
                spacing={1}
                alignItems="flex-start"
              >
                <TextField
                  fullWidth
                  size="small"
                  label={t(
                    "settings.configForms.nameKicks.rulesEditor.ruleLabel",
                    { number: index + 1 }
                  )}
                  value={pattern}
                  disabled={disabled}
                  error={!String(pattern).trim()}
                  helperText={
                    !String(pattern).trim()
                      ? t(
                          "settings.configForms.nameKicks.rulesEditor.emptyRule"
                        )
                      : undefined
                  }
                  onChange={(event) => updatePattern(index, event.target.value)}
                  inputProps={{
                    "data-testid": `name-kick-rule-${index}`,
                    spellCheck: false,
                  }}
                  sx={{
                    "& input": {
                      fontFamily:
                        '"SFMono-Regular", Consolas, "Liberation Mono", monospace',
                    },
                  }}
                />
                <Tooltip
                  title={t(
                    "settings.configForms.nameKicks.rulesEditor.deleteRule"
                  )}
                >
                  <span>
                    <IconButton
                      color="error"
                      disabled={disabled}
                      aria-label={t(
                        "settings.configForms.nameKicks.rulesEditor.deleteRule"
                      )}
                      onClick={() =>
                        onChange(
                          patterns.filter((_, itemIndex) => itemIndex !== index)
                        )
                      }
                    >
                      <DeleteOutlineIcon />
                    </IconButton>
                  </span>
                </Tooltip>
              </Stack>
            ))}
          </Stack>
        )}

        <Stack
          direction={{ xs: "column", sm: "row" }}
          spacing={1}
          sx={{ mt: 1.5 }}
        >
          <TextField
            fullWidth
            size="small"
            label={t("settings.configForms.nameKicks.rulesEditor.customLabel")}
            placeholder={t(
              "settings.configForms.nameKicks.rulesEditor.customPlaceholder"
            )}
            value={customPattern}
            disabled={disabled}
            onChange={(event) => setCustomPattern(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                addCustomPattern();
              }
            }}
            inputProps={{ spellCheck: false }}
          />
          <Button
            variant="outlined"
            startIcon={<AddOutlinedIcon />}
            disabled={disabled || !customPattern.trim()}
            onClick={addCustomPattern}
            sx={{ minWidth: { sm: 190 } }}
          >
            {t("settings.configForms.nameKicks.rulesEditor.addCustom")}
          </Button>
        </Stack>
      </Box>

      <Box data-theme-surface="panel"
        sx={{
          p: 1.5,
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.default",
          borderRadius: 0,
        }}
      >
        <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
          <ScienceOutlinedIcon color="primary" fontSize="small" />
          <Box>
            <Typography variant="body2" fontWeight={900}>
              {t("settings.configForms.nameKicks.rulesEditor.testTitle")}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {t("settings.configForms.nameKicks.rulesEditor.testHelp")}
            </Typography>
          </Box>
        </Stack>
        <TextField
          fullWidth
          size="small"
          label={t("settings.configForms.nameKicks.rulesEditor.testLabel")}
          placeholder={t(
            "settings.configForms.nameKicks.rulesEditor.testPlaceholder"
          )}
          value={testName}
          onChange={(event) => setTestName(event.target.value)}
          inputProps={{ "data-testid": "name-kick-test-name" }}
        />
        {testName && (
          <Alert
            severity={preview.matches.length ? "error" : "success"}
            sx={{ mt: 1.25 }}
            data-testid="name-kick-test-result"
          >
            <Typography variant="body2" fontWeight={850}>
              {t(
                preview.matches.length
                  ? "settings.configForms.nameKicks.rulesEditor.testKick"
                  : "settings.configForms.nameKicks.rulesEditor.testAllow",
                { name: testName }
              )}
            </Typography>
            {preview.matches.length > 0 && (
              <Typography variant="caption">
                {t("settings.configForms.nameKicks.rulesEditor.testMatched", {
                  number: preview.matches[0].index + 1,
                })}
              </Typography>
            )}
            {preview.unsupported.length > 0 && (
              <Typography variant="caption" display="block">
                {t(
                  "settings.configForms.nameKicks.rulesEditor.testUnsupported",
                  { count: preview.unsupported.length }
                )}
              </Typography>
            )}
          </Alert>
        )}
      </Box>
    </Stack>
  );
}
