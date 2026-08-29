import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Autocomplete,
  Box,
  Chip,
  CircularProgress,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import { useTranslation } from "react-i18next";
import { get } from "@/utils/fetchUtils";

const DEFAULT_ROOT = "settings.configForms.playerFlagPicker";

const optionLabel = (option) =>
  typeof option === "string" ? option : option?.flag || "";

const normalizeFlags = (values) => [
  ...new Set(
    (values || [])
      .map(optionLabel)
      .map((value) => value.trim())
      .filter(Boolean)
  ),
];

export default function PlayerFlagPicker({
  value = [],
  disabled = false,
  onChange,
  translationRoot = DEFAULT_ROOT,
  label,
  help,
  error,
  showNotice = true,
}) {
  const { t } = useTranslation();
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const selectedFlags = useMemo(() => normalizeFlags(value), [value]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadFailed(false);

    get("get_available_player_flags")
      .then((response) => response.json())
      .then((payload) => {
        if (cancelled) return;
        setOptions(
          Array.isArray(payload?.result?.flags) ? payload.result.flags : []
        );
      })
      .catch((loadError) => {
        if (cancelled) return;
        console.warn("Unable to load player flag catalogue", loadError);
        setLoadFailed(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const fieldHelp = error
    ? error
    : loadFailed
    ? t(`${translationRoot}.loadFailed`)
    : help || t(`${translationRoot}.help`);

  return (
    <Stack spacing={1.5} data-testid="player-flag-picker">
      {showNotice && (
        <Alert
          severity="info"
          icon={<ShieldOutlinedIcon />}
          sx={{ borderRadius: 0 }}
        >
          <Typography variant="body2" fontWeight={800}>
            {t(`${translationRoot}.noticeTitle`)}
          </Typography>
          <Typography variant="body2">
            {t(`${translationRoot}.noticeBody`)}
          </Typography>
        </Alert>
      )}

      <Autocomplete
        multiple
        freeSolo
        filterSelectedOptions
        options={options}
        value={selectedFlags}
        disabled={disabled}
        loading={loading}
        getOptionLabel={optionLabel}
        isOptionEqualToValue={(option, selected) =>
          optionLabel(option) === optionLabel(selected)
        }
        onChange={(_, nextValue) => onChange?.(normalizeFlags(nextValue))}
        noOptionsText={t(`${translationRoot}.noOptions`)}
        loadingText={t(`${translationRoot}.loading`)}
        renderOption={(props, option) => {
          const { key, ...optionProps } = props;
          return (
            <Box
              component="li"
              {...optionProps}
              key={key || option.flag}
              sx={{
                display: "flex !important",
                justifyContent: "space-between !important",
                gap: 2,
              }}
            >
              <Typography variant="body2" fontWeight={750}>
                {option.flag}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t(`${translationRoot}.playerCount`, {
                  count: option.player_count || 0,
                })}
              </Typography>
            </Box>
          );
        }}
        renderTags={(tagValue, getTagProps) =>
          tagValue.map((flag, index) => {
            const { key, ...tagProps } = getTagProps({ index });
            return (
              <Chip
                {...tagProps}
                key={key || flag}
                label={flag}
                size="small"
                variant="outlined"
                sx={{ borderRadius: 0, fontWeight: 750 }}
              />
            );
          })
        }
        renderInput={(params) => (
          <TextField
            {...params}
            error={Boolean(error)}
            label={label || t(`${translationRoot}.label`)}
            placeholder={
              selectedFlags.length
                ? undefined
                : t(`${translationRoot}.placeholder`)
            }
            helperText={fieldHelp}
            InputProps={{
              ...params.InputProps,
              endAdornment: (
                <>
                  {loading ? <CircularProgress size={18} /> : null}
                  {params.InputProps.endAdornment}
                </>
              ),
            }}
          />
        )}
        sx={{
          "& .MuiOutlinedInput-root": {
            borderRadius: 0,
            bgcolor: "background.default",
          },
          "& .MuiAutocomplete-paper": { borderRadius: 0 },
        }}
      />

      {!loading && options.length > 0 && (
        <Typography variant="caption" color="text.secondary">
          {t(`${translationRoot}.catalogueCount`, { count: options.length })}
        </Typography>
      )}
    </Stack>
  );
}
