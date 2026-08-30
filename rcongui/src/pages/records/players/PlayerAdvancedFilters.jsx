import {
  Autocomplete,
  Box,
  Button,
  Chip,
  FormControlLabel,
  IconButton,
  Popover,
  Skeleton,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import AddReactionIcon from "@mui/icons-material/AddReaction";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import { lazy, Suspense, useMemo, useState } from "react";
import countries from "country-list";
import emojiData from "@emoji-mart/data/sets/15/twitter.json";
import Emoji from "@/components/shared/Emoji";
import { CountryFlag } from "@/components/shared/CountryFlag";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { DateTimePicker } from "@mui/x-date-pickers/DateTimePicker";
import dayjs from "dayjs";
import { useTranslation } from "react-i18next";

const EmojiPicker = lazy(() => import("@emoji-mart/react"));
const countryCodes = countries.getCodes();

const asDayjs = (value) => {
  if (!value) return null;
  return dayjs.isDayjs(value) ? value : dayjs(value);
};

export default function PlayerAdvancedFilters({
  compact,
  formFields,
  handleInputChange,
  handleReset,
  navigationState,
  selectedCountry,
  selectedEmoji,
  setFormFields,
  setSelectedCountry,
  setSelectedEmoji,
}) {
  const { t, i18n } = useTranslation();
  const [anchorEl, setAnchorEl] = useState(null);
  const countryOptions = useMemo(() => {
    const language = i18n.resolvedLanguage === "en" ? "en" : "de";
    const displayNames = new Intl.DisplayNames([language], { type: "region" });
    return countryCodes.map((code) => ({
      code: code.toLowerCase(),
      name: displayNames.of(code) || countries.getName(code),
    }));
  }, [i18n.resolvedLanguage]);

  const countryField = (
    <Autocomplete
      openText={t("common.openOptions")}
      closeText={t("common.closeOptions")}
      clearText={t("common.clearSelection")}
      noOptionsText={t("common.noResults")}
      options={countryOptions}
      getOptionLabel={(option) => option.name}
      value={
        countryOptions.find((country) => country.code === selectedCountry) ||
        null
      }
      onChange={(_event, newValue) => setSelectedCountry(newValue?.code || "")}
      sx={{ width: "100%", minWidth: compact ? 0 : 180 }}
      renderOption={({ key, ...props }, option) => (
        <li key={key} {...props}>
          <Stack direction="row" spacing={1} alignItems="center">
            <CountryFlag country={option.code} />
            <span>{option.name}</span>
          </Stack>
        </li>
      )}
      renderInput={(params) => (
        <>
          <TextField {...params} label={t("records.players.country")} size="small" />
          <input type="hidden" name="country" value={selectedCountry ?? ""} />
        </>
      )}
    />
  );

  return (
    <Box
      id="player-advanced-filters"
      sx={{ borderTop: (theme) => `1px solid ${theme.palette.divider}`, pt: 1.25 }}
    >
      <Stack spacing={1.25}>
        {compact ? (
          <Stack spacing={1}>
            <TextField
              value={formFields.player_id}
              onChange={handleInputChange}
              label={t("records.players.playerId")}
              name="player_id"
              size="small"
              fullWidth
            />
            {countryField}
            <Button
              variant="outlined"
              color="secondary"
              startIcon={<RestartAltIcon />}
              onClick={handleReset}
              disabled={navigationState === "loading"}
              sx={{ minHeight: 44 }}
            >
              {t("records.players.reset")}
            </Button>
          </Stack>
        ) : null}

        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={1}
          alignItems={{ xs: "stretch", md: "center" }}
        >
          {!compact ? <Box sx={{ flex: "0 1 220px" }}>{countryField}</Box> : null}
          <Stack
            direction="row"
            spacing={1}
            alignItems="center"
            justifyContent="space-between"
            sx={{
              flex: { xs: "0 0 auto", md: "1 1 260px" },
              minHeight: 44,
              border: (theme) => `1px solid ${theme.palette.divider}`,
              borderRadius: 0,
              px: 1,
            }}
          >
            <Stack direction="row" spacing={0.75} alignItems="center" flexWrap="wrap" useFlexGap>
              {selectedEmoji.map((emoji) => (
                <Chip
                  key={emoji.id}
                  size="small"
                  label={<Emoji emoji={emoji} size={18} />}
                  onDelete={() =>
                    setSelectedEmoji(selectedEmoji.filter((item) => item.id !== emoji.id))
                  }
                />
              ))}
              {selectedEmoji.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  {t("records.players.filterFlags")}
                </Typography>
              ) : null}
            </Stack>
            <IconButton
              onClick={(event) => setAnchorEl(event.currentTarget)}
              aria-label={t("records.players.addFlagFilter")}
              sx={{ minHeight: 44, minWidth: 44 }}
            >
              <AddReactionIcon />
            </IconButton>
          </Stack>

          <LocalizationProvider dateAdapter={AdapterDayjs}>
            <DateTimePicker
              localeText={{ openDatePickerDialogue: () => t("common.chooseDate") }}
              value={asDayjs(formFields.last_seen_from)}
              onChange={(newValue) =>
                setFormFields((previous) => ({ ...previous, last_seen_from: newValue }))
              }
              label={t("records.players.lastSeenFrom")}
              name="last_seen_from"
              format="DD.MM.YYYY HH:mm"
              ampm={false}
              slotProps={{ textField: { size: "small", sx: { minWidth: { md: 210 } } } }}
            />
            <DateTimePicker
              localeText={{ openDatePickerDialogue: () => t("common.chooseDate") }}
              value={asDayjs(formFields.last_seen_till)}
              onChange={(newValue) =>
                setFormFields((previous) => ({ ...previous, last_seen_till: newValue }))
              }
              label={t("records.players.lastSeenUntil")}
              name="last_seen_till"
              format="DD.MM.YYYY HH:mm"
              ampm={false}
              slotProps={{ textField: { size: "small", sx: { minWidth: { md: 210 } } } }}
            />
          </LocalizationProvider>
        </Stack>

        <Stack direction="row" spacing={{ xs: 1, md: 2 }} flexWrap="wrap" useFlexGap>
          {[
            ["blacklisted", "blacklistedOnly"],
            ["exact_name_match", "exactName"],
            ["ignore_accent", "ignoreAccent"],
            ["is_watched", "watchedOnly"],
          ].map(([name, label]) => (
            <FormControlLabel
              key={name}
              control={
                <Switch
                  size="small"
                  name={name}
                  checked={formFields[name]}
                  onChange={handleInputChange}
                />
              }
              label={t(`records.players.${label}`)}
            />
          ))}
        </Stack>
      </Stack>

      <Popover
        open={Boolean(anchorEl)}
        anchorEl={anchorEl}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
      >
        <Suspense fallback={<Skeleton variant="rectangular" height={400} width={300} />}>
          <EmojiPicker
            set="twitter"
            data={emojiData}
            onEmojiSelect={(emoji) => {
              if (selectedEmoji.some((item) => item.id === emoji.id)) return;
              setSelectedEmoji([...selectedEmoji, emoji]);
            }}
          />
        </Suspense>
      </Popover>
    </Box>
  );
}
