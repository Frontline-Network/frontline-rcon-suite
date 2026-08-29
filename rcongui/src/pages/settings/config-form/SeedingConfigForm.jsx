import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Chip,
  Divider,
  FormControlLabel,
  InputAdornment,
  LinearProgress,
  Slider,
  Stack,
  Switch,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import CampaignOutlinedIcon from "@mui/icons-material/CampaignOutlined";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import FlagOutlinedIcon from "@mui/icons-material/FlagOutlined";
import GavelOutlinedIcon from "@mui/icons-material/GavelOutlined";
import Groups2OutlinedIcon from "@mui/icons-material/Groups2Outlined";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import NotificationsNoneOutlinedIcon from "@mui/icons-material/NotificationsNoneOutlined";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import SportsEsportsOutlinedIcon from "@mui/icons-material/SportsEsportsOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import { useTranslation } from "react-i18next";
import { getAllRoles } from "@/constants/roles";
import { get } from "@/utils/fetchUtils";
import StableNumberField from "./StableNumberField";

const ROOT = "settings.configForms.seedingWorkbench";

const sectionIcons = {
  operation: <VisibilityOutlinedIcon fontSize="small" />,
  rules: <FlagOutlinedIcon fontSize="small" />,
  exemptions: <ShieldOutlinedIcon fontSize="small" />,
  actions: <GavelOutlinedIcon fontSize="small" />,
  notifications: <NotificationsNoneOutlinedIcon fontSize="small" />,
};

const cardSx = {
  border: "1px solid",
  borderColor: "divider",
  bgcolor: "background.default",
  borderRadius: 0,
};

const normalizeMap = (value) => {
  if (Array.isArray(value)) {
    return Object.fromEntries(value.map((item) => [item, item]));
  }
  return value && typeof value === "object" ? value : {};
};

const isNestedRule = (value) =>
  Boolean(value && typeof value === "object" && !Array.isArray(value));

function SectionHeader({ section }) {
  const { t } = useTranslation();
  return (
    <Stack direction="row" spacing={1.25} alignItems="flex-start">
      <Box
        sx={{
          display: "grid",
          placeItems: "center",
          width: 38,
          height: 38,
          flex: "0 0 auto",
          color: "primary.main",
          bgcolor: "action.selected",
          border: "1px solid",
          borderColor: "divider",
          borderRadius: 0,
        }}
      >
        {sectionIcons[section]}
      </Box>
      <Box>
        <Typography component="h2" variant="h6" fontWeight={850}>
          {t(`${ROOT}.sections.${section}.title`)}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
          {t(`${ROOT}.sections.${section}.description`)}
        </Typography>
      </Box>
    </Stack>
  );
}

function LabeledNumber({
  label,
  help,
  value,
  onChange,
  disabled,
  min = 0,
  max,
  unit,
}) {
  return (
    <Stack spacing={0.65} sx={{ minWidth: 0 }}>
      <Typography variant="body2" fontWeight={750}>
        {label}
      </Typography>
      <StableNumberField
        size="small"
        value={value}
        disabled={disabled}
        onChange={onChange}
        inputProps={{ min, max }}
        InputProps={{
          endAdornment: unit ? (
            <InputAdornment position="end">{unit}</InputAdornment>
          ) : undefined,
        }}
      />
      {help && (
        <Typography variant="caption" color="text.secondary">
          {help}
        </Typography>
      )}
    </Stack>
  );
}

function SwitchCard({ checked, disabled, title, description, onChange, icon }) {
  return (
    <Box sx={{ ...cardSx, p: 1.5 }}>
      <FormControlLabel
        sx={{ m: 0, width: "100%", alignItems: "flex-start", gap: 0.75 }}
        control={
          <Switch
            checked={Boolean(checked)}
            disabled={disabled}
            onChange={(event) => onChange(event.target.checked)}
          />
        }
        label={
          <Stack direction="row" spacing={1} alignItems="flex-start">
            {icon && <Box sx={{ color: "primary.main", mt: 0.2 }}>{icon}</Box>}
            <Box>
              <Typography variant="body2" fontWeight={800}>
                {title}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {description}
              </Typography>
            </Box>
          </Stack>
        }
      />
    </Box>
  );
}

function MessageEditor({
  label,
  help,
  value,
  disabled,
  onChange,
  placeholders = [],
  rows = 3,
}) {
  const { t } = useTranslation();
  const appendPlaceholder = (placeholder) => {
    const current = value || "";
    onChange(
      `${current}${current && !current.endsWith(" ") ? " " : ""}${placeholder}`
    );
  };

  return (
    <Stack spacing={0.8}>
      <Box>
        <Typography variant="body2" fontWeight={750}>
          {label}
        </Typography>
        {help && (
          <Typography variant="caption" color="text.secondary">
            {help}
          </Typography>
        )}
      </Box>
      <TextField
        value={value || ""}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        multiline
        minRows={rows}
        fullWidth
      />
      {placeholders.length > 0 && (
        <Stack direction="row" spacing={0.6} useFlexGap flexWrap="wrap">
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ alignSelf: "center", mr: 0.25 }}
          >
            {t(`${ROOT}.placeholders`)}
          </Typography>
          {placeholders.map((placeholder) => (
            <Chip
              key={placeholder}
              label={placeholder.replace(/[{}]/g, "")}
              size="small"
              variant="outlined"
              disabled={disabled}
              onClick={() => appendPlaceholder(placeholder)}
              sx={{ height: 24, borderRadius: 0 }}
            />
          ))}
        </Stack>
      )}
    </Stack>
  );
}

function PlayerWindow({ rule, disabled, onChange }) {
  const { t } = useTranslation();
  const minimum = Math.max(0, Math.min(100, Number(rule.min_players) || 0));
  const maximum = Math.max(
    minimum,
    Math.min(100, Number(rule.max_players) || minimum)
  );
  return (
    <Stack spacing={1.25}>
      <Typography variant="overline" color="text.secondary">
        {t(`${ROOT}.fields.playerWindow`, {
          defaultValue: "Gültig für Spieleranzahl",
        })}
      </Typography>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "minmax(0, 1fr) minmax(0, 1fr)",
            md: "112px minmax(180px, 1fr) 112px",
          },
          gap: { xs: 1, md: 2 },
          alignItems: "center",
        }}
      >
        <StableNumberField
          size="small"
          value={rule.min_players ?? 0}
          disabled={disabled}
          onChange={(value) => onChange({ min_players: value })}
          inputProps={{
            min: 0,
            max: 100,
            "aria-label": t(`${ROOT}.fields.fromPlayers`),
          }}
        />
        <Slider
          value={[minimum, maximum]}
          disabled={disabled}
          min={0}
          max={100}
          valueLabelDisplay="auto"
          onChange={(_, [min_players, max_players]) =>
            onChange({ min_players, max_players })
          }
          sx={{
            gridColumn: { xs: "1 / -1", md: "auto" },
            gridRow: { xs: 2, md: "auto" },
            mx: { xs: 0.75, md: 0 },
            "& .MuiSlider-rail, & .MuiSlider-track, & .MuiSlider-thumb": {
              borderRadius: 0,
            },
          }}
        />
        <StableNumberField
          size="small"
          value={rule.max_players ?? 100}
          disabled={disabled}
          onChange={(value) => onChange({ max_players: value })}
          inputProps={{
            min: 0,
            max: 100,
            "aria-label": t(`${ROOT}.fields.untilPlayers`),
          }}
        />
      </Box>
      <Stack direction="row" justifyContent="space-between" spacing={1}>
        <Typography variant="caption" color="text.secondary">
          {t(`${ROOT}.fields.fromPlayers`)}: {minimum}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {t(`${ROOT}.fields.untilPlayers`)}: {maximum} {t(`${ROOT}.players`)}
        </Typography>
      </Stack>
    </Stack>
  );
}

function RuleShell({ icon, title, description, active, children }) {
  const { t } = useTranslation();
  return (
    <Box
      sx={{
        overflow: "hidden",
        border: "1px solid",
        borderColor: "rgba(214, 184, 112, 0.26)",
        bgcolor: "rgba(16, 20, 16, 0.72)",
        borderRadius: 0,
      }}
    >
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={1.5}
        justifyContent="space-between"
        alignItems={{ xs: "stretch", sm: "flex-start" }}
        sx={{ p: 1.75 }}
      >
        <Stack direction="row" spacing={1.1} alignItems="flex-start">
          <Box
            sx={{
              display: "grid",
              placeItems: "center",
              width: 34,
              height: 34,
              flex: "0 0 auto",
              color: active ? "primary.main" : "text.secondary",
              bgcolor: "action.selected",
              border: "1px solid",
              borderColor: "divider",
              borderRadius: 0,
            }}
          >
            {icon}
          </Box>
          <Box>
            <Typography variant="subtitle1" fontWeight={850}>
              {title}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {description}
            </Typography>
          </Box>
        </Stack>
        <Chip
          label={t(`${ROOT}.status.${active ? "active" : "incomplete"}`)}
          color={active ? "success" : "default"}
          size="small"
          variant={active ? "filled" : "outlined"}
          sx={{ borderRadius: 0, fontWeight: 800 }}
        />
      </Stack>
      <Divider sx={{ borderColor: "rgba(214, 184, 112, 0.16)" }} />
      <Stack spacing={2} sx={{ p: 1.75 }}>
        {children}
      </Stack>
    </Box>
  );
}

const getRuleMeta = (data) => {
  const roles = isNestedRule(data.disallowed_roles)
    ? normalizeMap(data.disallowed_roles.roles)
    : normalizeMap(data.disallowed_roles);
  const weapons = isNestedRule(data.disallowed_weapons)
    ? normalizeMap(data.disallowed_weapons.weapons)
    : normalizeMap(data.disallowed_weapons);
  const cap = isNestedRule(data.enforce_cap_fight)
    ? data.enforce_cap_fight
    : { min_players: 1, max_players: data.enforce_cap_fight ? 50 : 0 };

  return {
    roles: {
      active:
        Object.keys(roles).length > 0 &&
        (!isNestedRule(data.disallowed_roles) ||
          Number(data.disallowed_roles.max_players) > 0),
      count: Object.keys(roles).length,
      min: data.disallowed_roles?.min_players ?? 1,
      max: data.disallowed_roles?.max_players ?? 40,
    },
    weapons: {
      active:
        Object.keys(weapons).length > 0 &&
        (!isNestedRule(data.disallowed_weapons) ||
          Number(data.disallowed_weapons.max_players) > 0),
      count: Object.keys(weapons).length,
      min: data.disallowed_weapons?.min_players ?? 1,
      max: data.disallowed_weapons?.max_players ?? 40,
    },
    cap: {
      active: Number(cap.max_players) > 0,
      count: Number(cap.max_caps) || 0,
      min: cap.min_players ?? 1,
      max: cap.max_players ?? 50,
    },
  };
};

function RuleOverviewCard({
  icon,
  title,
  meta,
  detail,
  selected,
  disabled,
  onSelect,
}) {
  const { t } = useTranslation();
  return (
    <Button
      type="button"
      onClick={onSelect}
      disabled={disabled}
      aria-pressed={selected}
      sx={{
        position: "relative",
        minHeight: 104,
        p: 1.75,
        justifyContent: "flex-start",
        textAlign: "left",
        color: "text.primary",
        border: "1px solid",
        borderColor: selected
          ? "rgba(214, 184, 112, 0.5)"
          : "rgba(214, 184, 112, 0.16)",
        borderLeftWidth: selected ? 3 : 1,
        bgcolor: selected
          ? "rgba(214, 170, 77, 0.08)"
          : "rgba(14, 18, 14, 0.6)",
        borderRadius: 0,
        textTransform: "none",
        transition: "border-color 160ms ease, background-color 160ms ease",
        "&:hover": {
          bgcolor: "rgba(214, 170, 77, 0.1)",
          borderColor: "rgba(214, 184, 112, 0.46)",
        },
      }}
    >
      <Stack
        direction="row"
        spacing={1.25}
        alignItems="flex-start"
        width="100%"
      >
        <Box
          sx={{
            display: "grid",
            placeItems: "center",
            width: 38,
            height: 38,
            flex: "0 0 auto",
            color: selected ? "primary.main" : "text.secondary",
            bgcolor: "rgba(214, 170, 77, 0.08)",
            borderRadius: 0,
          }}
        >
          {icon}
        </Box>
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Stack direction="row" justifyContent="space-between" spacing={1}>
            <Typography variant="subtitle2" fontWeight={800}>
              {title}
            </Typography>
            <Chip
              label={t(
                `${ROOT}.status.${meta.active ? "active" : "incomplete"}`
              )}
              color={meta.active ? "success" : "default"}
              size="small"
              variant="outlined"
              sx={{ height: 22, borderRadius: 0 }}
            />
          </Stack>
          <Typography
            variant="caption"
            color="text.secondary"
            display="block"
            sx={{ mt: 0.5 }}
          >
            {meta.min}–{meta.max} {t(`${ROOT}.players`)} · {detail}
          </Typography>
          <LinearProgress
            variant="determinate"
            value={Math.min(100, Math.max(0, Number(meta.max) || 0))}
            sx={{ mt: 1.25, height: 3, bgcolor: "action.hover" }}
          />
        </Box>
      </Stack>
    </Button>
  );
}

function RuleEffectPreview({ selectedRule, meta }) {
  const { t } = useTranslation();
  const current = meta[selectedRule];
  const titles = {
    roles: t(`${ROOT}.rules.roles.title`),
    weapons: t(`${ROOT}.rules.weapons.title`),
    cap: t(`${ROOT}.rules.cap.title`),
  };
  return (
    <Box
      component="aside"
      aria-label={t(`${ROOT}.effectPreview.title`, {
        defaultValue: "So wirkt die Regel",
      })}
      sx={{
        p: 2,
        borderLeft: { lg: "1px solid" },
        borderTop: { xs: "1px solid", lg: 0 },
        borderColor: "rgba(214, 184, 112, 0.16)",
        bgcolor: "rgba(8, 11, 8, 0.42)",
      }}
    >
      <Typography variant="overline" color="primary.main">
        {t(`${ROOT}.effectPreview.title`, {
          defaultValue: "So wirkt die Regel",
        })}
      </Typography>
      <Typography variant="h6" fontWeight={800} sx={{ mt: 0.35 }}>
        {titles[selectedRule]}
      </Typography>
      <Typography
        variant="body2"
        color="text.secondary"
        sx={{ mt: 1, lineHeight: 1.7 }}
      >
        {current.active
          ? t(`${ROOT}.effectPreview.active`, {
              defaultValue:
                "Die Regel greift zwischen {{min}} und {{max}} Spielern und prüft {{count}} konfigurierte Einträge.",
              min: current.min,
              max: current.max,
              count: current.count,
            })
          : t(`${ROOT}.effectPreview.inactive`, {
              defaultValue:
                "Diese Regel ist noch nicht vollständig eingerichtet und greift aktuell nicht ein.",
            })}
      </Typography>
      <Alert severity={current.active ? "success" : "warning"} sx={{ mt: 2 }}>
        {current.active
          ? t(`${ROOT}.effectPreview.valid`, {
              defaultValue: "Die Regel ist einsatzbereit.",
            })
          : t(`${ROOT}.effectPreview.missing`, {
              defaultValue: "Ergänze die Regel, bevor du sie aktiv einsetzt.",
            })}
      </Alert>
    </Box>
  );
}

function RolesRule({ value, disabled, onChange }) {
  const { t } = useTranslation();
  const nested = isNestedRule(value);
  const rule = nested
    ? value
    : { min_players: 1, max_players: 40, roles: normalizeMap(value) };
  const roleMap = normalizeMap(rule.roles);
  const roleOptions = useMemo(
    () =>
      getAllRoles().map((role) => ({
        ...role,
        label: t(`settings.configForms.roles.${role.value}`, {
          defaultValue: role.label,
        }),
      })),
    [t]
  );
  const selected = Object.keys(roleMap).map(
    (role) =>
      roleOptions.find((option) => option.value === role) || {
        value: role,
        label: roleMap[role] || role,
      }
  );
  const patch = (next) =>
    onChange(
      nested ? { ...rule, ...next } : Object.keys(next.roles || roleMap)
    );

  return (
    <RuleShell
      icon={<Groups2OutlinedIcon fontSize="small" />}
      title={t(`${ROOT}.rules.roles.title`)}
      description={t(`${ROOT}.rules.roles.description`)}
      active={selected.length > 0 && Number(rule.max_players) > 0}
    >
      {nested && (
        <PlayerWindow
          rule={rule}
          disabled={disabled}
          onChange={(next) => patch(next)}
        />
      )}
      <Autocomplete
        multiple
        options={roleOptions}
        value={selected}
        disabled={disabled}
        isOptionEqualToValue={(option, selectedOption) =>
          option.value === selectedOption.value
        }
        onChange={(_, nextRoles) =>
          patch({
            roles: Object.fromEntries(
              nextRoles.map((role) => [role.value, role.label])
            ),
          })
        }
        renderInput={(params) => (
          <TextField
            {...params}
            label={t(`${ROOT}.fields.blockedRoles`)}
            helperText={t(`${ROOT}.fields.blockedRolesHelp`)}
          />
        )}
      />
      {nested && (
        <MessageEditor
          label={t(`${ROOT}.fields.violationMessage`)}
          help={t(`${ROOT}.fields.roleMessageHelp`)}
          value={rule.violation_message}
          disabled={disabled}
          onChange={(violation_message) => patch({ violation_message })}
          placeholders={["{role}"]}
          rows={2}
        />
      )}
    </RuleShell>
  );
}

function WeaponsEditor({ value, options = [], disabled, onChange }) {
  const { t } = useTranslation();
  const entries = Object.entries(normalizeMap(value));
  const [pickerValue, setPickerValue] = useState("");
  const optionByName = useMemo(
    () => new Map(options.map((option) => [option.name, option])),
    [options]
  );
  const availableOptions = useMemo(() => {
    const selected = new Set(entries.map(([weaponKey]) => weaponKey));
    return options
      .filter((option) => !selected.has(option.name))
      .sort(
        (left, right) =>
          left.type.localeCompare(right.type) ||
          left.name.localeCompare(right.name)
      );
  }, [entries, options]);

  const weaponTypeLabel = (type) =>
    t(`${ROOT}.weaponTypes.${type || "unknown"}`, {
      defaultValue: type || t(`${ROOT}.weaponTypes.unknown`),
    });

  const defaultReadableName = (name, type) => {
    if (["artillery", "commander", "pak", "self_propelled_artillery"].includes(type)) {
      return weaponTypeLabel(type);
    }
    return name;
  };

  const addWeapon = (selection) => {
    const name =
      typeof selection === "string"
        ? selection.trim()
        : String(selection?.name || "").trim();
    if (!name || Object.prototype.hasOwnProperty.call(value || {}, name)) return;

    const type =
      typeof selection === "string"
        ? optionByName.get(name)?.type
        : selection?.type;
    onChange({
      ...normalizeMap(value),
      [name]: defaultReadableName(name, type),
    });
    setPickerValue("");
  };

  const updateEntry = (index, key, label) => {
    const nextEntries = [...entries];
    nextEntries[index] = [key, label];
    onChange(
      Object.fromEntries(nextEntries.filter(([weaponKey]) => weaponKey.trim()))
    );
  };

  return (
    <Stack spacing={1}>
      <Autocomplete
        freeSolo
        clearOnBlur
        options={availableOptions}
        inputValue={pickerValue}
        disabled={disabled}
        noOptionsText={t(`${ROOT}.fields.noWeaponMatches`)}
        getOptionLabel={(option) =>
          typeof option === "string" ? option : option.name
        }
        groupBy={(option) => weaponTypeLabel(option.type)}
        onInputChange={(_, nextValue, reason) =>
          setPickerValue(reason === "reset" ? "" : nextValue)
        }
        onChange={(_, selection) => addWeapon(selection)}
        renderOption={(props, option) => (
          <Box
            component="li"
            {...props}
            sx={{
              display: "flex !important",
              alignItems: "center",
              justifyContent: "space-between !important",
              gap: 1.5,
            }}
          >
            <Typography variant="body2">{option.name}</Typography>
            <Typography variant="caption" color="text.secondary">
              {weaponTypeLabel(option.type)}
            </Typography>
          </Box>
        )}
        renderInput={(params) => (
          <TextField
            {...params}
            size="small"
            label={t(`${ROOT}.fields.weaponPicker`)}
            helperText={t(`${ROOT}.fields.weaponPickerHelp`)}
          />
        )}
      />
      {entries.length === 0 && (
        <Alert severity="info" icon={<InfoOutlinedIcon />}>
          {t(`${ROOT}.rules.weapons.empty`)}
        </Alert>
      )}
      {entries.map(([weaponKey, label], index) => (
        <Box
          key={`${weaponKey}-${index}`}
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              sm: "minmax(0, 1.4fr) minmax(0, 1fr) auto",
            },
            gap: 1,
            alignItems: "start",
          }}
        >
          <Box
            sx={{
              minHeight: 40,
              px: 1.5,
              py: 0.75,
              border: "1px solid",
              borderColor: "divider",
              bgcolor: "background.paper",
            }}
          >
            <Typography variant="body2" fontWeight={750}>
              {weaponKey}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {weaponTypeLabel(optionByName.get(weaponKey)?.type)}
            </Typography>
          </Box>
          <TextField
            size="small"
            label={t(`${ROOT}.fields.weaponLabel`)}
            value={label}
            disabled={disabled}
            onChange={(event) =>
              updateEntry(index, weaponKey, event.target.value)
            }
          />
          <Button
            color="inherit"
            disabled={disabled}
            onClick={() =>
              onChange(
                Object.fromEntries(
                  entries.filter((_, itemIndex) => itemIndex !== index)
                )
              )
            }
            aria-label={t(`${ROOT}.fields.removeWeapon`)}
            sx={{ minWidth: 40, height: 40, px: 1 }}
          >
            <DeleteOutlineIcon fontSize="small" />
          </Button>
        </Box>
      ))}
    </Stack>
  );
}

function WeaponsRule({ value, weaponOptions, disabled, onChange }) {
  const { t } = useTranslation();
  const nested = isNestedRule(value);
  const rule = nested
    ? value
    : { min_players: 1, max_players: 40, weapons: normalizeMap(value) };
  const weapons = normalizeMap(rule.weapons);
  const patch = (next) =>
    onChange(
      nested ? { ...rule, ...next } : Object.keys(next.weapons || weapons)
    );

  return (
    <RuleShell
      icon={<SportsEsportsOutlinedIcon fontSize="small" />}
      title={t(`${ROOT}.rules.weapons.title`)}
      description={t(`${ROOT}.rules.weapons.description`)}
      active={Object.keys(weapons).length > 0 && Number(rule.max_players) > 0}
    >
      {nested && (
        <PlayerWindow rule={rule} disabled={disabled} onChange={patch} />
      )}
      <WeaponsEditor
        value={weapons}
        options={weaponOptions}
        disabled={disabled}
        onChange={(nextWeapons) => patch({ weapons: nextWeapons })}
      />
      {nested && (
        <MessageEditor
          label={t(`${ROOT}.fields.violationMessage`)}
          help={t(`${ROOT}.fields.weaponMessageHelp`)}
          value={rule.violation_message}
          disabled={disabled}
          onChange={(violation_message) => patch({ violation_message })}
          placeholders={["{weapon}"]}
          rows={2}
        />
      )}
    </RuleShell>
  );
}

function CapRule({ value, disabled, onChange }) {
  const { t } = useTranslation();
  const nested = isNestedRule(value);
  const rule = nested
    ? value
    : {
        min_players: 1,
        max_players: value ? 50 : 0,
        max_caps: 3,
        skip_warning: true,
      };
  const active = nested ? Number(rule.max_players) > 0 : Boolean(value);
  const patch = (next) =>
    onChange(nested ? { ...rule, ...next } : Boolean(next.max_players));

  return (
    <RuleShell
      icon={<FlagOutlinedIcon fontSize="small" />}
      title={t(`${ROOT}.rules.cap.title`)}
      description={t(`${ROOT}.rules.cap.description`)}
      active={active}
    >
      <SwitchCard
        checked={active}
        disabled={disabled}
        title={t(`${ROOT}.rules.cap.switchTitle`)}
        description={t(`${ROOT}.rules.cap.switchHelp`)}
        onChange={(checked) => patch({ max_players: checked ? 50 : 0 })}
      />
      {nested && active && (
        <>
          <PlayerWindow rule={rule} disabled={disabled} onChange={patch} />
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                sm: "minmax(0, 1fr) minmax(0, 1.25fr)",
              },
              gap: 1.5,
            }}
          >
            <LabeledNumber
              label={t(`${ROOT}.fields.maxCaps`)}
              help={t(`${ROOT}.fields.maxCapsHelp`)}
              value={rule.max_caps ?? 3}
              onChange={(max_caps) => patch({ max_caps })}
              disabled={disabled}
              min={2}
              max={4}
            />
            <SwitchCard
              checked={rule.skip_warning}
              disabled={disabled}
              title={t(`${ROOT}.fields.directPunish`)}
              description={t(`${ROOT}.fields.directPunishHelp`)}
              onChange={(skip_warning) => patch({ skip_warning })}
            />
          </Box>
          <MessageEditor
            label={t(`${ROOT}.fields.violationMessage`)}
            help={t(`${ROOT}.fields.capMessageHelp`)}
            value={rule.violation_message}
            disabled={disabled}
            onChange={(violation_message) => patch({ violation_message })}
            rows={2}
          />
        </>
      )}
    </RuleShell>
  );
}

function RulesSection({ data, weaponOptions, disabled, patch }) {
  const { t } = useTranslation();
  const [selectedRule, setSelectedRule] = useState("roles");
  const meta = getRuleMeta(data);
  const ruleCards = [
    {
      id: "roles",
      icon: <Groups2OutlinedIcon fontSize="small" />,
      title: t(`${ROOT}.rules.roles.title`),
      detail: t(`${ROOT}.summary.roles`, { count: meta.roles.count }),
    },
    {
      id: "weapons",
      icon: <SportsEsportsOutlinedIcon fontSize="small" />,
      title: t(`${ROOT}.rules.weapons.title`),
      detail: t(`${ROOT}.summary.weapons`, { count: meta.weapons.count }),
    },
    {
      id: "cap",
      icon: <FlagOutlinedIcon fontSize="small" />,
      title: t(`${ROOT}.rules.cap.title`),
      detail: t(`${ROOT}.summary.capActive`),
    },
  ];

  return (
    <Stack spacing={1.5}>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "repeat(3, minmax(0, 1fr))" },
          gap: 1,
        }}
      >
        {ruleCards.map((rule) => (
          <RuleOverviewCard
            key={rule.id}
            icon={rule.icon}
            title={rule.title}
            detail={rule.detail}
            meta={meta[rule.id]}
            selected={selectedRule === rule.id}
            disabled={disabled}
            onSelect={() => setSelectedRule(rule.id)}
          />
        ))}
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "minmax(0, 1fr)",
            lg: "minmax(0, 1.9fr) minmax(260px, 0.8fr)",
          },
          border: "1px solid",
          borderColor: "rgba(214, 184, 112, 0.24)",
          bgcolor: "rgba(12, 16, 12, 0.54)",
          borderRadius: 0,
          overflow: "hidden",
        }}
      >
        <Box sx={{ p: { xs: 1, sm: 1.5 } }}>
          {selectedRule === "roles" && (
            <RolesRule
              value={data.disallowed_roles}
              disabled={disabled}
              onChange={(disallowed_roles) => patch({ disallowed_roles })}
            />
          )}
          {selectedRule === "weapons" && (
            <WeaponsRule
              value={data.disallowed_weapons}
              weaponOptions={weaponOptions}
              disabled={disabled}
              onChange={(disallowed_weapons) => patch({ disallowed_weapons })}
            />
          )}
          {selectedRule === "cap" && (
            <CapRule
              value={data.enforce_cap_fight}
              disabled={disabled}
              onChange={(enforce_cap_fight) => patch({ enforce_cap_fight })}
            />
          )}
        </Box>
        <RuleEffectPreview selectedRule={selectedRule} meta={meta} />
      </Box>
    </Stack>
  );
}

export function SeedingOperationModeControl({
  data,
  disabled = false,
  onChange,
}) {
  const { t } = useTranslation();
  const mode = !data.enabled ? "off" : data.dry_run ? "observe" : "active";
  return (
    <ToggleButtonGroup
      value={mode}
      exclusive
      disabled={disabled}
      onChange={(_, nextMode) => {
        if (!nextMode) return;
        onChange?.({
          enabled: nextMode !== "off",
          dry_run: nextMode === "observe",
        });
      }}
      aria-label={t(`${ROOT}.operation.modeTitle`)}
      size="small"
      sx={{
        "& .MuiToggleButton-root": {
          minHeight: 44,
          minWidth: { xs: 0, sm: 112 },
          px: { xs: 1.25, sm: 2 },
          borderRadius: 0,
          textTransform: "none",
          fontWeight: 800,
        },
        "& .MuiToggleButton-root.Mui-selected": {
          bgcolor: mode === "active" ? "success.dark" : "action.selected",
          color: mode === "active" ? "success.contrastText" : "text.primary",
        },
      }}
    >
      <ToggleButton value="off">{t(`${ROOT}.operation.off`)}</ToggleButton>
      <ToggleButton value="observe">
        {t(`${ROOT}.operation.observe`)}
      </ToggleButton>
      <ToggleButton value="active">
        {t(`${ROOT}.operation.active`)}
      </ToggleButton>
    </ToggleButtonGroup>
  );
}

function CountControl({ value, disabled, onChange, allowUnlimited = true }) {
  const { t } = useTranslation();
  const mode =
    Number(value) === 0 ? "skip" : Number(value) === -1 ? "unlimited" : "count";

  return (
    <Stack spacing={1}>
      <ToggleButtonGroup
        exclusive
        fullWidth
        size="small"
        value={mode}
        disabled={disabled}
        onChange={(_, nextMode) => {
          if (!nextMode) return;
          if (nextMode === "skip") onChange(0);
          if (nextMode === "unlimited") onChange(-1);
          if (nextMode === "count") onChange(Number(value) > 0 ? value : 1);
        }}
      >
        <ToggleButton value="skip">{t(`${ROOT}.count.skip`)}</ToggleButton>
        <ToggleButton value="count">{t(`${ROOT}.count.fixed`)}</ToggleButton>
        {allowUnlimited && (
          <ToggleButton value="unlimited">
            {t(`${ROOT}.count.unlimited`)}
          </ToggleButton>
        )}
      </ToggleButtonGroup>
      {mode === "count" && (
        <LabeledNumber
          label={t(`${ROOT}.fields.count`)}
          value={value}
          onChange={onChange}
          disabled={disabled}
          min={1}
          max={20}
        />
      )}
    </Stack>
  );
}

function StageCard({ number, title, description, status, children }) {
  return (
    <Box sx={{ ...cardSx, p: 1.75 }}>
      <Stack
        direction="row"
        spacing={1.25}
        alignItems="flex-start"
        sx={{ mb: 1.75 }}
      >
        <Box
          sx={{
            display: "grid",
            placeItems: "center",
            width: 28,
            height: 28,
            flex: "0 0 auto",
            border: "1px solid",
            borderColor: "primary.main",
            color: "primary.main",
            fontWeight: 900,
            borderRadius: 0,
          }}
        >
          {number}
        </Box>
        <Box sx={{ flex: 1 }}>
          <Stack
            direction="row"
            spacing={1}
            alignItems="center"
            useFlexGap
            flexWrap="wrap"
          >
            <Typography variant="subtitle1" fontWeight={850}>
              {title}
            </Typography>
            {status && (
              <Chip
                label={status}
                size="small"
                variant="outlined"
                sx={{ borderRadius: 0 }}
              />
            )}
          </Stack>
          <Typography variant="caption" color="text.secondary">
            {description}
          </Typography>
        </Box>
      </Stack>
      <Stack spacing={1.75}>{children}</Stack>
    </Box>
  );
}

function OperationSection({ data, disabled, patch }) {
  const { t } = useTranslation();
  return (
    <Stack spacing={2}>
      <LabeledNumber
        label={t(`${ROOT}.fields.globalMinimum`)}
        help={t(`${ROOT}.fields.globalMinimumHelp`)}
        value={data.dont_do_anything_below_this_number_of_players ?? 0}
        onChange={(dont_do_anything_below_this_number_of_players) =>
          patch({ dont_do_anything_below_this_number_of_players })
        }
        disabled={disabled}
        min={0}
        max={100}
        unit={t(`${ROOT}.players`)}
      />
      <Alert severity="info" icon={<InfoOutlinedIcon />}>
        {t(`${ROOT}.operation.note`)}
      </Alert>
    </Stack>
  );
}

function ExemptionsSection({ data, disabled, patch }) {
  const { t } = useTranslation();
  const roleOptions = useMemo(
    () =>
      getAllRoles().map((role) => ({
        ...role,
        label: t(`settings.configForms.roles.${role.value}`, {
          defaultValue: role.label,
        }),
      })),
    [t]
  );
  const selectedRoles = (data.immune_roles || []).map(
    (role) =>
      roleOptions.find((option) => option.value === role) || {
        value: role,
        label: role,
      }
  );

  return (
    <Stack spacing={2}>
      <Autocomplete
        multiple
        freeSolo
        options={[]}
        value={data.whitelist_flags || []}
        disabled={disabled}
        onChange={(_, whitelist_flags) => patch({ whitelist_flags })}
        renderInput={(params) => (
          <TextField
            {...params}
            label={t(`${ROOT}.fields.flags`)}
            helperText={t(`${ROOT}.fields.flagsHelp`)}
          />
        )}
      />
      <Autocomplete
        multiple
        options={roleOptions}
        value={selectedRoles}
        disabled={disabled}
        isOptionEqualToValue={(option, selectedOption) =>
          option.value === selectedOption.value
        }
        onChange={(_, roles) =>
          patch({ immune_roles: roles.map((role) => role.value) })
        }
        renderInput={(params) => (
          <TextField
            {...params}
            label={t(`${ROOT}.fields.immuneRoles`)}
            helperText={t(`${ROOT}.fields.immuneRolesHelp`)}
          />
        )}
      />
      <LabeledNumber
        label={t(`${ROOT}.fields.immuneLevel`)}
        help={t(`${ROOT}.fields.immuneLevelHelp`)}
        value={data.immune_player_level ?? 0}
        onChange={(immune_player_level) => patch({ immune_player_level })}
        disabled={disabled}
        min={0}
        max={500}
        unit={t(`${ROOT}.level`)}
      />
    </Stack>
  );
}

function ActionsSection({ data, disabled, patch }) {
  const { t } = useTranslation();
  const warningStatus =
    Number(data.number_of_warnings) === 0
      ? t(`${ROOT}.status.skipped`)
      : Number(data.number_of_warnings) === -1
      ? t(`${ROOT}.status.unlimited`)
      : t(`${ROOT}.status.times`, { count: data.number_of_warnings ?? 0 });
  const punishStatus =
    Number(data.number_of_punishments) === 0
      ? t(`${ROOT}.status.skipped`)
      : Number(data.number_of_punishments) === -1
      ? t(`${ROOT}.status.unlimited`)
      : t(`${ROOT}.status.times`, { count: data.number_of_punishments ?? 0 });

  return (
    <Stack spacing={1.5}>
      <StageCard
        number={1}
        title={t(`${ROOT}.actions.announcement.title`)}
        description={t(`${ROOT}.actions.announcement.description`)}
        status={
          data.announcement_enabled
            ? t(`${ROOT}.status.active`)
            : t(`${ROOT}.status.skipped`)
        }
      >
        <SwitchCard
          checked={data.announcement_enabled}
          disabled={disabled}
          icon={<CampaignOutlinedIcon fontSize="small" />}
          title={t(`${ROOT}.fields.announcementEnabled`)}
          description={t(`${ROOT}.fields.announcementEnabledHelp`)}
          onChange={(announcement_enabled) => patch({ announcement_enabled })}
        />
        {data.announcement_enabled && (
          <MessageEditor
            label={t(`${ROOT}.fields.announcementMessage`)}
            value={data.announcement_message}
            disabled={disabled}
            onChange={(announcement_message) => patch({ announcement_message })}
            placeholders={[
              "{disallowed_roles}",
              "{disallowed_roles_max_players}",
              "{disallowed_weapons}",
              "{disallowed_weapons_max_players}",
            ]}
          />
        )}
      </StageCard>
      <StageCard
        number={2}
        title={t(`${ROOT}.actions.warning.title`)}
        description={t(`${ROOT}.actions.warning.description`)}
        status={warningStatus}
      >
        <CountControl
          value={data.number_of_warnings}
          disabled={disabled}
          onChange={(number_of_warnings) => patch({ number_of_warnings })}
        />
        {Number(data.number_of_warnings) !== 0 && (
          <>
            <LabeledNumber
              label={t(`${ROOT}.fields.interval`)}
              value={data.warning_interval_seconds ?? 60}
              onChange={(warning_interval_seconds) =>
                patch({ warning_interval_seconds })
              }
              disabled={disabled}
              min={0}
              unit={t(`${ROOT}.seconds`)}
            />
            <MessageEditor
              label={t(`${ROOT}.fields.warningMessage`)}
              value={data.warning_message}
              disabled={disabled}
              onChange={(warning_message) => patch({ warning_message })}
              placeholders={[
                "{player_name}",
                "{violation}",
                "{max_warnings}",
                "{received_warnings}",
                "{next_check_seconds}",
              ]}
            />
          </>
        )}
      </StageCard>
      <StageCard
        number={3}
        title={t(`${ROOT}.actions.punish.title`)}
        description={t(`${ROOT}.actions.punish.description`)}
        status={punishStatus}
      >
        <CountControl
          value={data.number_of_punishments}
          disabled={disabled}
          onChange={(number_of_punishments) => patch({ number_of_punishments })}
        />
        {Number(data.number_of_punishments) !== 0 && (
          <>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr 1fr" },
                gap: 1.25,
              }}
            >
              <LabeledNumber
                label={t(`${ROOT}.fields.interval`)}
                value={data.punish_interval_seconds ?? 60}
                onChange={(punish_interval_seconds) =>
                  patch({ punish_interval_seconds })
                }
                disabled={disabled}
                min={0}
                unit={t(`${ROOT}.seconds`)}
              />
              <LabeledNumber
                label={t(`${ROOT}.fields.minSquad`)}
                value={data.min_squad_players_for_punish ?? 0}
                onChange={(min_squad_players_for_punish) =>
                  patch({ min_squad_players_for_punish })
                }
                disabled={disabled}
                min={0}
                max={6}
              />
              <LabeledNumber
                label={t(`${ROOT}.fields.minServer`)}
                value={data.min_server_players_for_punish ?? 0}
                onChange={(min_server_players_for_punish) =>
                  patch({ min_server_players_for_punish })
                }
                disabled={disabled}
                min={0}
                max={100}
              />
            </Box>
            <MessageEditor
              label={t(`${ROOT}.fields.punishMessage`)}
              value={data.punish_message}
              disabled={disabled}
              onChange={(punish_message) => patch({ punish_message })}
              placeholders={[
                "{player_name}",
                "{violation}",
                "{max_punishes}",
                "{received_punishes}",
                "{next_check_seconds}",
              ]}
            />
          </>
        )}
      </StageCard>
      <StageCard
        number={4}
        title={t(`${ROOT}.actions.kick.title`)}
        description={t(`${ROOT}.actions.kick.description`)}
        status={
          data.kick_after_max_punish
            ? t(`${ROOT}.status.active`)
            : t(`${ROOT}.status.skipped`)
        }
      >
        <SwitchCard
          checked={data.kick_after_max_punish}
          disabled={disabled}
          icon={<LockOutlinedIcon fontSize="small" />}
          title={t(`${ROOT}.fields.kickEnabled`)}
          description={t(`${ROOT}.fields.kickEnabledHelp`)}
          onChange={(kick_after_max_punish) => patch({ kick_after_max_punish })}
        />
        {data.kick_after_max_punish && (
          <>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr 1fr" },
                gap: 1.25,
              }}
            >
              <LabeledNumber
                label={t(`${ROOT}.fields.gracePeriod`)}
                value={data.kick_grace_period_seconds ?? 60}
                onChange={(kick_grace_period_seconds) =>
                  patch({ kick_grace_period_seconds })
                }
                disabled={disabled}
                min={0}
                unit={t(`${ROOT}.seconds`)}
              />
              <LabeledNumber
                label={t(`${ROOT}.fields.minSquad`)}
                value={data.min_squad_players_for_kick ?? 0}
                onChange={(min_squad_players_for_kick) =>
                  patch({ min_squad_players_for_kick })
                }
                disabled={disabled}
                min={0}
                max={6}
              />
              <LabeledNumber
                label={t(`${ROOT}.fields.minServer`)}
                value={data.min_server_players_for_kick ?? 0}
                onChange={(min_server_players_for_kick) =>
                  patch({ min_server_players_for_kick })
                }
                disabled={disabled}
                min={0}
                max={100}
              />
            </Box>
            <MessageEditor
              label={t(`${ROOT}.fields.kickMessage`)}
              value={data.kick_message}
              disabled={disabled}
              onChange={(kick_message) => patch({ kick_message })}
              placeholders={[
                "{player_name}",
                "{violation}",
                "{kick_grace_period}",
              ]}
            />
          </>
        )}
      </StageCard>
    </Stack>
  );
}

function NotificationsSection({ data, disabled, patch }) {
  const { t } = useTranslation();
  return (
    <Stack spacing={2}>
      <Alert severity="info" icon={<InfoOutlinedIcon />}>
        {t(`${ROOT}.notifications.note`)}
      </Alert>
      <TextField
        type="url"
        label={t(`${ROOT}.fields.webhook`)}
        helperText={t(`${ROOT}.fields.webhookHelp`)}
        placeholder="https://discord.com/api/webhooks/…"
        value={data.discord_webhook_url || ""}
        disabled={disabled}
        onChange={(event) =>
          patch({ discord_webhook_url: event.target.value || null })
        }
        fullWidth
      />
    </Stack>
  );
}

export default function SeedingConfigForm({
  data,
  activeSection,
  disabled = false,
  onChange,
}) {
  const [weaponOptions, setWeaponOptions] = useState([]);
  const patch = (nextData) => onChange?.(nextData);

  useEffect(() => {
    let cancelled = false;
    get("get_available_weapons")
      .then((response) => response.json())
      .then((payload) => {
        if (!cancelled) {
          setWeaponOptions(
            Array.isArray(payload?.result?.weapons)
              ? payload.result.weapons
              : []
          );
        }
      })
      .catch((error) => {
        if (!cancelled) {
          console.warn("Unable to load the weapon catalogue", error);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Stack
      spacing={2.25}
      data-testid="seeding-config-form"
      data-section={activeSection}
    >
      <SectionHeader section={activeSection} />
      <Divider sx={{ borderColor: "rgba(214, 184, 112, 0.16)" }} />
      {activeSection === "operation" && (
        <OperationSection data={data} disabled={disabled} patch={patch} />
      )}
      {activeSection === "rules" && (
        <RulesSection
          data={data}
          weaponOptions={weaponOptions}
          disabled={disabled}
          patch={patch}
        />
      )}
      {activeSection === "exemptions" && (
        <ExemptionsSection data={data} disabled={disabled} patch={patch} />
      )}
      {activeSection === "actions" && (
        <ActionsSection data={data} disabled={disabled} patch={patch} />
      )}
      {activeSection === "notifications" && (
        <NotificationsSection data={data} disabled={disabled} patch={patch} />
      )}
    </Stack>
  );
}
