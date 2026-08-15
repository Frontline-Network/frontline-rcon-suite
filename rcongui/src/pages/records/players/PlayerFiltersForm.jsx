import {
  Autocomplete,
  Badge,
  Box,
  Button,
  Chip,
  Collapse,
  FormControlLabel,
  IconButton,
  InputAdornment,
  Popover,
  Skeleton,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import AddReactionIcon from "@mui/icons-material/AddReaction";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import SearchIcon from "@mui/icons-material/Search";
import TuneIcon from "@mui/icons-material/Tune";
import { Form, useNavigation, useSubmit } from "react-router-dom";
import { CountryFlag } from "@/components/shared/CountryFlag";
import { lazy, Suspense, useMemo, useState } from "react";
import countries from "country-list";
import emojiData from "@emoji-mart/data/sets/15/twitter.json";
import Emoji from "@/components/shared/Emoji";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { DateTimePicker } from "@mui/x-date-pickers/DateTimePicker";
import dayjs from "dayjs";
import { useTranslation } from "react-i18next";

const EmojiPicker = lazy(() => import("@emoji-mart/react"));
const countryCodes = countries.getCodes();

export default function PlayerFiltersForm({ fields }) {
  const { t, i18n } = useTranslation();
  const submit = useSubmit();
  const navigation = useNavigation();
  const hasAdvancedFilters = Boolean(
    fields.flags?.length ||
      fields.last_seen_from ||
      fields.last_seen_till ||
      fields.blacklisted ||
      fields.exact_name_match ||
      fields.ignore_accent ||
      fields.is_watched
  );
  const [advancedOpen, setAdvancedOpen] = useState(hasAdvancedFilters);
  const [formFields, setFormFields] = useState({
    player_name: fields.player_name || "",
    player_id: fields.player_id || "",
    blacklisted: !!fields.blacklisted,
    exact_name_match: !!fields.exact_name_match,
    ignore_accent: !!fields.ignore_accent,
    is_watched: !!fields.is_watched,
    last_seen_from: fields.last_seen_from ? dayjs(fields.last_seen_from) : null,
    last_seen_till: fields.last_seen_till ? dayjs(fields.last_seen_till) : null,
  });
  const [selectedCountry, setSelectedCountry] = useState(fields.country);
  const [selectedEmoji, setSelectedEmoji] = useState(fields.flags);
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);
  const countryOptions = useMemo(() => {
    const language = i18n.resolvedLanguage === "en" ? "en" : "de";
    const displayNames = new Intl.DisplayNames([language], { type: "region" });
    return countryCodes.map((code) => ({
      code: code.toLowerCase(),
      name: displayNames.of(code) || countries.getName(code),
    }));
  }, [i18n.resolvedLanguage]);

  const advancedFilterCount = useMemo(
    () =>
      [
        selectedEmoji.length > 0,
        Boolean(formFields.last_seen_from),
        Boolean(formFields.last_seen_till),
        formFields.blacklisted,
        formFields.exact_name_match,
        formFields.ignore_accent,
        formFields.is_watched,
      ].filter(Boolean).length,
    [formFields, selectedEmoji.length]
  );

  const handleReset = () => {
    setFormFields({
      player_name: "",
      player_id: "",
      blacklisted: false,
      exact_name_match: false,
      ignore_accent: false,
      is_watched: false,
      last_seen_from: null,
      last_seen_till: null,
    });
    setSelectedCountry("");
    setSelectedEmoji([]);
    setAdvancedOpen(false);
    submit(null, { method: "GET" });
  };

  const handleInputChange = (event) => {
    const { name, value, checked } = event.target;
    setFormFields((previous) => ({
      ...previous,
      [name]: event.target.type === "checkbox" ? checked : value,
    }));
  };

  return (
    <Form method="GET">
      <Stack
        spacing={1}
        sx={{
          width: "100%",
          border: (theme) => `1px solid ${theme.palette.divider}`,
          borderRadius: 1,
          bgcolor: "background.paper",
          p: { xs: 1, md: 1.25 },
        }}
      >
        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={1}
          alignItems={{ xs: "stretch", md: "center" }}
        >
          <TextField
            value={formFields.player_name}
            onChange={handleInputChange}
            label={t("records.players.playerName")}
            name="player_name"
            size="small"
            sx={{
              width: "100%",
              flex: { xs: "0 0 auto", md: "1 1 280px" },
            }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
            }}
          />

          <TextField
            value={formFields.player_id}
            onChange={handleInputChange}
            label={t("records.players.playerId")}
            name="player_id"
            size="small"
            sx={{
              width: "100%",
              flex: { xs: "0 0 auto", md: "1 1 260px" },
            }}
          />

          <Autocomplete
            openText={t("common.openOptions")}
            closeText={t("common.closeOptions")}
            clearText={t("common.clearSelection")}
            noOptionsText={t("common.noResults")}
            options={countryOptions}
            getOptionLabel={(option) => option.name}
            value={
              countryOptions.find(
                (country) => country.code === selectedCountry
              ) || null
            }
            onChange={(event, newValue) =>
              setSelectedCountry(newValue?.code || "")
            }
            sx={{
              width: "100%",
              flex: { xs: "0 0 auto", md: "0 1 220px" },
              minWidth: { md: 180 },
            }}
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
                <TextField
                  {...params}
                  label={t("records.players.country")}
                  size="small"
                />
                <input
                  type="hidden"
                  name="country"
                  value={selectedCountry ?? ""}
                />
              </>
            )}
          />

          <Button
            type="submit"
            variant="contained"
            color="primary"
            startIcon={<SearchIcon />}
            disabled={navigation.state === "loading"}
            sx={{ minHeight: 40, minWidth: 118 }}
          >
            {t("common.search")}
          </Button>

          <Button
            variant="outlined"
            color="secondary"
            startIcon={<RestartAltIcon />}
            onClick={handleReset}
            disabled={navigation.state === "loading"}
            sx={{ minHeight: 40 }}
          >
            {t("records.players.reset")}
          </Button>

          <Button
            variant="outlined"
            color="inherit"
            startIcon={
              <Badge badgeContent={advancedFilterCount} color="primary">
                <TuneIcon />
              </Badge>
            }
            endIcon={
              <ExpandMoreIcon
                sx={{
                  transform: advancedOpen ? "rotate(180deg)" : "none",
                  transition: (theme) => theme.transitions.create("transform"),
                }}
              />
            }
            aria-expanded={advancedOpen}
            aria-controls="player-advanced-filters"
            onClick={() => setAdvancedOpen((value) => !value)}
            sx={{ minHeight: 40, whiteSpace: "nowrap" }}
          >
            {t("records.players.moreFilters")}
          </Button>
        </Stack>

        <Collapse in={advancedOpen} unmountOnExit>
          <Box
            id="player-advanced-filters"
            sx={{
              borderTop: (theme) => `1px solid ${theme.palette.divider}`,
              pt: 1.25,
            }}
          >
            <Stack spacing={1.25}>
              <Stack
                direction={{ xs: "column", md: "row" }}
                spacing={1}
                alignItems={{ xs: "stretch", md: "center" }}
              >
                <Stack
                  direction="row"
                  spacing={1}
                  alignItems="center"
                  justifyContent="space-between"
                  sx={{
                    flex: { xs: "0 0 auto", md: "1 1 260px" },
                    minHeight: 40,
                    border: (theme) => `1px solid ${theme.palette.divider}`,
                    borderRadius: 1,
                    px: 1,
                  }}
                >
                  <Stack
                    direction="row"
                    spacing={0.75}
                    alignItems="center"
                    flexWrap="wrap"
                    useFlexGap
                  >
                    {selectedEmoji.map((emoji) => (
                      <Chip
                        key={emoji.id}
                        size="small"
                        label={<Emoji emoji={emoji} size={18} />}
                        onDelete={() =>
                          setSelectedEmoji(
                            selectedEmoji.filter((item) => item.id !== emoji.id)
                          )
                        }
                      />
                    ))}
                    {selectedEmoji.length === 0 && (
                      <Typography variant="body2" color="text.secondary">
                        {t("records.players.filterFlags")}
                      </Typography>
                    )}
                  </Stack>
                  <IconButton
                    size="small"
                    onClick={(event) => setAnchorEl(event.currentTarget)}
                    aria-label={t("records.players.addFlagFilter")}
                  >
                    <AddReactionIcon />
                  </IconButton>
                </Stack>

                <LocalizationProvider dateAdapter={AdapterDayjs}>
                  <DateTimePicker
                    localeText={{
                      openDatePickerDialogue: () => t("common.chooseDate"),
                    }}
                    value={formFields.last_seen_from}
                    onChange={(newValue) =>
                      setFormFields((previous) => ({
                        ...previous,
                        last_seen_from: newValue,
                      }))
                    }
                    label={t("records.players.lastSeenFrom")}
                    name="last_seen_from"
                    format="DD.MM.YYYY HH:mm"
                    ampm={false}
                    slotProps={{
                      textField: { size: "small", sx: { minWidth: 210 } },
                    }}
                  />
                </LocalizationProvider>

                <LocalizationProvider dateAdapter={AdapterDayjs}>
                  <DateTimePicker
                    localeText={{
                      openDatePickerDialogue: () => t("common.chooseDate"),
                    }}
                    value={formFields.last_seen_till}
                    onChange={(newValue) =>
                      setFormFields((previous) => ({
                        ...previous,
                        last_seen_till: newValue,
                      }))
                    }
                    label={t("records.players.lastSeenUntil")}
                    name="last_seen_till"
                    format="DD.MM.YYYY HH:mm"
                    ampm={false}
                    slotProps={{
                      textField: { size: "small", sx: { minWidth: 210 } },
                    }}
                  />
                </LocalizationProvider>
              </Stack>

              <Stack
                direction="row"
                spacing={{ xs: 1, md: 2 }}
                flexWrap="wrap"
                useFlexGap
              >
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
          </Box>
        </Collapse>
      </Stack>

      <Popover
        open={open}
        anchorEl={anchorEl}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
      >
        <Suspense
          fallback={<Skeleton variant="rectangular" height={400} width={300} />}
        >
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
      <input
        type="hidden"
        name="flags"
        value={selectedEmoji.map((emoji) => emoji.native).join(",")}
      />
    </Form>
  );
}
