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
import FilterAltOutlinedIcon from "@mui/icons-material/FilterAltOutlined";
import RestartAltOutlinedIcon from "@mui/icons-material/RestartAltOutlined";
import SearchOutlinedIcon from "@mui/icons-material/SearchOutlined";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { getMapEnvironmentLabel, getMapModeLabel } from "@/utils/mapLabels";
import { unifiedGamemodeName } from "./objectives/helpers";

/**
 * Shared, compact map-catalog filter. It deliberately exposes the complete
 * filter state through visible labels so the same control works in the map
 * switcher, rotation builder, and on narrow touch layouts.
 */
export const MapFilter = ({ maps = [], onFilterChange, compact = false }) => {
  const { t } = useTranslation();
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedMode, setSelectedMode] = useState("all");
  const [selectedEnvironment, setSelectedEnvironment] = useState("all");

  const modes = useMemo(
    () =>
      Array.from(
        new Set(maps.map((map) => unifiedGamemodeName(map.game_mode)))
      ).sort(),
    [maps]
  );
  const environments = useMemo(
    () => Array.from(new Set(maps.map((map) => map.environment))).sort(),
    [maps]
  );

  const filteredMaps = useMemo(() => {
    const query = searchTerm.trim().toLocaleLowerCase();
    return maps.filter((mapLayer) => {
      const haystack = `${mapLayer.map.pretty_name} ${mapLayer.id}`.toLocaleLowerCase();
      const matchesSearch = !query || haystack.includes(query);
      const matchesMode =
        selectedMode === "all" ||
        unifiedGamemodeName(mapLayer.game_mode) === selectedMode;
      const matchesEnvironment =
        selectedEnvironment === "all" ||
        mapLayer.environment === selectedEnvironment;
      return matchesSearch && matchesMode && matchesEnvironment;
    });
  }, [maps, searchTerm, selectedEnvironment, selectedMode]);

  useEffect(() => {
    onFilterChange(filteredMaps);
  }, [filteredMaps, onFilterChange]);

  const hasFilters =
    Boolean(searchTerm) ||
    selectedMode !== "all" ||
    selectedEnvironment !== "all";

  const resetFilters = () => {
    setSearchTerm("");
    setSelectedMode("all");
    setSelectedEnvironment("all");
  };

  return (
    <Box
      component="section"
      aria-label={t("maps.rotationWorkbench.filters")}
      sx={{
        p: compact ? 1.25 : 1.5,
        borderBottom: "1px solid",
        borderColor: "divider",
        bgcolor: "background.default",
      }}
    >
      {!compact && (
        <Stack
          direction="row"
          justifyContent="space-between"
          alignItems="center"
          sx={{ mb: 1.25 }}
        >
          <Stack direction="row" spacing={0.75} alignItems="center">
            <FilterAltOutlinedIcon color="primary" fontSize="small" />
            <Typography variant="overline" color="text.secondary">
              {t("maps.rotationWorkbench.filters")}
            </Typography>
          </Stack>
          <Typography variant="caption" color="text.secondary">
            {t("maps.rotationWorkbench.results", {
              count: filteredMaps.length,
            })}
          </Typography>
        </Stack>
      )}

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            sm: compact
              ? "minmax(0, 1fr) minmax(0, 1fr) auto"
              : "minmax(220px, 1.5fr) minmax(150px, 1fr) minmax(150px, 1fr) auto",
          },
          gap: 1,
          alignItems: "start",
        }}
      >
        <TextField
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
          label={t("maps.rotationWorkbench.searchLabel")}
          placeholder={t("maps.filter")}
          size="small"
          fullWidth
          sx={{
            gridColumn: {
              sm: compact ? "1 / -1" : "auto",
            },
          }}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchOutlinedIcon fontSize="small" />
                </InputAdornment>
              ),
            },
          }}
        />

        <FormControl size="small" fullWidth>
          <InputLabel id="map-filter-mode-label">{t("maps.gameMode")}</InputLabel>
          <Select
            labelId="map-filter-mode-label"
            value={selectedMode}
            label={t("maps.gameMode")}
            onChange={(event) => setSelectedMode(event.target.value)}
          >
            <MenuItem value="all">
              {t("maps.votemapWorkbench.allModes")}
            </MenuItem>
            {modes.map((mode) => (
              <MenuItem key={mode} value={mode}>
                {getMapModeLabel(t, mode)}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <FormControl size="small" fullWidth>
          <InputLabel id="map-filter-environment-label">
            {t("maps.weather")}
          </InputLabel>
          <Select
            labelId="map-filter-environment-label"
            value={selectedEnvironment}
            label={t("maps.weather")}
            onChange={(event) => setSelectedEnvironment(event.target.value)}
          >
            <MenuItem value="all">
              {t("maps.votemapWorkbench.allEnvironments")}
            </MenuItem>
            {environments.map((environment) => (
              <MenuItem key={environment} value={environment}>
                {getMapEnvironmentLabel(t, environment)}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <Button
          variant="outlined"
          color="inherit"
          disabled={!hasFilters}
          onClick={resetFilters}
          startIcon={<RestartAltOutlinedIcon />}
          sx={{ minHeight: 40, whiteSpace: "nowrap" }}
        >
          {t("maps.rotationWorkbench.resetFilters")}
        </Button>
      </Box>
    </Box>
  );
};
