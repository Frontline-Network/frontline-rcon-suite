import {
  Badge,
  Button,
  Collapse,
  InputAdornment,
  Skeleton,
  Stack,
  TextField,
  useMediaQuery,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import SearchIcon from "@mui/icons-material/Search";
import TuneIcon from "@mui/icons-material/Tune";
import { Form, useNavigation, useSubmit } from "react-router-dom";
import { lazy, Suspense, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

const PlayerAdvancedFilters = lazy(() => import("./PlayerAdvancedFilters"));

export default function PlayerFiltersForm({ fields }) {
  const { t } = useTranslation();
  const submit = useSubmit();
  const navigation = useNavigation();
  const compact = useMediaQuery((theme) => theme.breakpoints.down("md"));
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
  const [advancedLoaded, setAdvancedLoaded] = useState(hasAdvancedFilters);
  const [formFields, setFormFields] = useState({
    player_name: fields.player_name || "",
    player_id: fields.player_id || "",
    blacklisted: !!fields.blacklisted,
    exact_name_match: !!fields.exact_name_match,
    ignore_accent: !!fields.ignore_accent,
    is_watched: !!fields.is_watched,
    last_seen_from: fields.last_seen_from || null,
    last_seen_till: fields.last_seen_till || null,
  });
  const [selectedCountry, setSelectedCountry] = useState(fields.country);
  const [selectedEmoji, setSelectedEmoji] = useState(fields.flags);

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
          borderRadius: 0,
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

          {!compact ? (
            <TextField
              value={formFields.player_id}
              onChange={handleInputChange}
              label={t("records.players.playerId")}
              name="player_id"
              size="small"
              sx={{
                width: "100%",
                flex: "1 1 260px",
              }}
            />
          ) : null}

          <Button
            type="submit"
            variant="contained"
            color="primary"
            startIcon={<SearchIcon />}
            disabled={navigation.state === "loading"}
            sx={{ minHeight: 44, minWidth: 118 }}
          >
            {t("common.search")}
          </Button>

          <Button
            variant="outlined"
            color="secondary"
            startIcon={<RestartAltIcon />}
            onClick={handleReset}
            disabled={navigation.state === "loading"}
            sx={{ display: { xs: "none", md: "inline-flex" }, minHeight: 40 }}
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
            onClick={() => {
              setAdvancedLoaded(true);
              setAdvancedOpen((value) => !value);
            }}
            sx={{ minHeight: 44, whiteSpace: "nowrap" }}
          >
            {t("records.players.moreFilters")}
          </Button>
        </Stack>

        <Collapse in={advancedOpen}>
          {advancedLoaded ? (
            <Suspense fallback={<Skeleton variant="rectangular" height={180} />}>
              <PlayerAdvancedFilters
                compact={compact}
                formFields={formFields}
                handleInputChange={handleInputChange}
                handleReset={handleReset}
                navigationState={navigation.state}
                selectedCountry={selectedCountry}
                selectedEmoji={selectedEmoji}
                setFormFields={setFormFields}
                setSelectedCountry={setSelectedCountry}
                setSelectedEmoji={setSelectedEmoji}
              />
            </Suspense>
          ) : null}
        </Collapse>
      </Stack>

      <input
        type="hidden"
        name="flags"
        value={selectedEmoji.map((emoji) => emoji.native).join(",")}
      />
    </Form>
  );
}
