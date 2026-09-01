import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Collapse,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  FormControlLabel,
  FormHelperText,
  IconButton,
  InputLabel,
  Menu,
  MenuItem,
  Radio,
  RadioGroup,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import AddIcon from "@mui/icons-material/Add";
import AdminPanelSettingsOutlinedIcon from "@mui/icons-material/AdminPanelSettingsOutlined";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import DownloadOutlinedIcon from "@mui/icons-material/DownloadOutlined";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import GroupOutlinedIcon from "@mui/icons-material/GroupOutlined";
import ImportExportOutlinedIcon from "@mui/icons-material/ImportExportOutlined";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import PersonOutlineIcon from "@mui/icons-material/PersonOutline";
import ReplayIcon from "@mui/icons-material/Replay";
import SaveOutlinedIcon from "@mui/icons-material/SaveOutlined";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import UploadFileOutlinedIcon from "@mui/icons-material/UploadFileOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import WorkspacePremiumOutlinedIcon from "@mui/icons-material/WorkspacePremiumOutlined";
import { useLoaderData, useNavigation, useSubmit } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { cmd } from "@/utils/fetchUtils";
import exportFile from "@/utils/exportFile";
import PlayerAutocompletion from "@/components/form/custom/PlayerAutocompletion";
import PageHeader from "@/components/shared/PageHeader";
import SectionSurface from "@/components/shared/SectionSurface";
import { SearchInput } from "@/components/shared/SearchInput";
import ConfigActionBar from "@/pages/settings/config-form/ConfigActionBar";
import { usePlayerSidebar } from "@/hooks/usePlayerSidebar";
import { isFakeMode } from "@/mirage/demo-data";

const INTENT = {
  ADD_ADMIN: "add_admin",
  DELETE_ADMIN: "delete_admin",
};

const ROLE_ORDER = ["senior", "junior", "spectator"];

const DEMO_ADMINS = [
  { player_id: "76561198000000001", name: "FLN_Raven", role: "senior" },
  { player_id: "76561198000000002", name: "FLN_Wolf", role: "spectator" },
  { player_id: "76561198000000003", name: "CommanderKane", role: "junior" },
  { player_id: "76561198000000004", name: "Major_Obvious", role: "senior" },
  { player_id: "76561198000000005", name: "SteelViper", role: "junior" },
  { player_id: "76561198000000006", name: "OldSchoolHero", role: "spectator" },
  { player_id: "76561198000000007", name: "TacticalTom", role: "senior" },
  { player_id: "76561198000000008", name: "FieldMedic", role: "spectator" },
];

const normalizeRole = (role) =>
  String(role ?? "")
    .trim()
    .toLowerCase();

const getRoleIcon = (role) => {
  switch (normalizeRole(role)) {
    case "senior":
      return WorkspacePremiumOutlinedIcon;
    case "junior":
      return ShieldOutlinedIcon;
    case "spectator":
      return VisibilityOutlinedIcon;
    default:
      return AdminPanelSettingsOutlinedIcon;
  }
};

const getRoleColor = (role) => {
  switch (normalizeRole(role)) {
    case "senior":
      return "warning";
    case "junior":
      return "info";
    case "spectator":
      return "secondary";
    default:
      return "primary";
  }
};

export const loader = async () => {
  if (isFakeMode()) {
    return {
      admins: DEMO_ADMINS,
      adminGroups: ["spectator", "junior", "senior"],
    };
  }

  const admins = await cmd.GET_CONSOLE_ADMINS();
  const adminGroups = await cmd.GET_CONSOLE_ADMIN_GROUPS();
  return { admins, adminGroups };
};

export const action = async ({ request }) => {
  const admins = await request.json();
  const results = [];

  for (const { intent, admin } of admins) {
    if (intent === INTENT.ADD_ADMIN) {
      results.push(
        await cmd.ADD_CONSOLE_ADMIN({
          payload: {
            description: admin.name,
            player_id: admin.player_id,
            role: normalizeRole(admin.role),
          },
        })
      );
    }

    if (intent === INTENT.DELETE_ADMIN) {
      results.push(
        await cmd.DELETE_CONSOLE_ADMIN({
          payload: { player_id: admin.player_id },
        })
      );
    }
  }

  return results;
};

function RoleIcon({ role, fontSize = "small" }) {
  const Icon = getRoleIcon(role);
  return <Icon fontSize={fontSize} />;
}

function RoleBadge({ role, label }) {
  const color = getRoleColor(role);

  return (
    <Stack
      direction="row"
      alignItems="center"
      spacing={0.75}
      sx={{
        width: "fit-content",
        minHeight: 32,
        px: 1,
        border: "1px solid",
        borderColor: `${color}.main`,
        color: `${color}.main`,
        bgcolor: (theme) => alpha(theme.palette[color].main, 0.06),
      }}
    >
      <RoleIcon role={role} />
      <Typography
        variant="caption"
        sx={{ fontWeight: 800, letterSpacing: "0.08em" }}
      >
        {label}
      </Typography>
    </Stack>
  );
}

function SummaryItem({ label, value, role }) {
  return (
    <Stack
      direction="row"
      alignItems="center"
      spacing={1}
      sx={{ minWidth: { xs: 0, sm: 120 }, px: { xs: 0.75, sm: 1.25 } }}
    >
      {role ? (
        <Box sx={{ color: `${getRoleColor(role)}.main`, display: "grid" }}>
          <RoleIcon role={role} />
        </Box>
      ) : (
        <GroupOutlinedIcon color="primary" fontSize="small" />
      )}
      <Box sx={{ minWidth: 0 }}>
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ display: "block", letterSpacing: "0.08em" }}
        >
          {label}
        </Typography>
        <Typography variant="h6" sx={{ lineHeight: 1, fontWeight: 800 }}>
          {value}
        </Typography>
      </Box>
    </Stack>
  );
}

export default function ConsoleAdminsPage() {
  const { admins: serverAdmins, adminGroups: rawAdminGroups } = useLoaderData();
  const { t } = useTranslation();
  const submit = useSubmit();
  const navigation = useNavigation();
  const { openWithId } = usePlayerSidebar();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));

  const adminGroups = useMemo(
    () =>
      rawAdminGroups.map(normalizeRole).sort((left, right) => {
        const leftIndex = ROLE_ORDER.indexOf(left);
        const rightIndex = ROLE_ORDER.indexOf(right);
        return (
          (leftIndex === -1 ? ROLE_ORDER.length : leftIndex) -
          (rightIndex === -1 ? ROLE_ORDER.length : rightIndex)
        );
      }),
    [rawAdminGroups]
  );
  const defaultRole = adminGroups.includes("spectator")
    ? "spectator"
    : adminGroups[0] ?? "";
  const initialAdmin = useMemo(
    () => ({ player_id: "", name: "", role: defaultRole }),
    [defaultRole]
  );

  const [admins, setAdmins] = useState(serverAdmins);
  const [removedIds, setRemovedIds] = useState(new Set());
  const [checked, setChecked] = useState(new Set());
  const [searched, setSearched] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [newAdmin, setNewAdmin] = useState(initialAdmin);
  const [editingRoleId, setEditingRoleId] = useState(null);
  const [addPanelOpen, setAddPanelOpen] = useState(false);
  const [toolsAnchor, setToolsAnchor] = useState(null);
  const [importPreview, setImportPreview] = useState(null);
  const [importMode, setImportMode] = useState("merge");
  const [saveConfirmOpen, setSaveConfirmOpen] = useState(false);

  const serverAdminMap = useMemo(
    () => new Map(serverAdmins.map((admin) => [admin.player_id, admin])),
    [serverAdmins]
  );

  useEffect(() => {
    setAdmins(serverAdmins);
    setRemovedIds(new Set());
    setChecked(new Set());
    setNewAdmin(initialAdmin);
    setEditingRoleId(null);
  }, [serverAdmins, initialAdmin]);

  const roleLabel = (role) => {
    const normalized = normalizeRole(role);
    const knownKey = {
      senior: "roleSenior",
      junior: "roleJunior",
      spectator: "roleSpectator",
    }[normalized];
    return knownKey
      ? t(`settings.consoleAdmins.${knownKey}`)
      : normalized.toUpperCase();
  };

  const roleDescription = (role) => {
    const normalized = normalizeRole(role);
    const knownKey = {
      senior: "roleSeniorDescription",
      junior: "roleJuniorDescription",
      spectator: "roleSpectatorDescription",
    }[normalized];
    return knownKey
      ? t(`settings.consoleAdmins.${knownKey}`)
      : t("settings.consoleAdmins.roleGenericDescription");
  };

  const changeTypeFor = (admin) => {
    if (removedIds.has(admin.player_id)) return "removed";
    const original = serverAdminMap.get(admin.player_id);
    if (!original) return "added";
    if (normalizeRole(original.role) !== normalizeRole(admin.role)) {
      return "role";
    }
    return "active";
  };

  const changes = useMemo(() => {
    let added = 0;
    let role = 0;

    admins.forEach((admin) => {
      if (removedIds.has(admin.player_id)) return;
      const original = serverAdminMap.get(admin.player_id);
      if (!original) added += 1;
      else if (normalizeRole(original.role) !== normalizeRole(admin.role)) {
        role += 1;
      }
    });

    return { added, role, removed: removedIds.size };
  }, [admins, removedIds, serverAdminMap]);

  const totalChanges = changes.added + changes.role + changes.removed;
  const hasChanges = totalChanges > 0;
  const isSaving = navigation.state !== "idle";

  const activeAdmins = useMemo(
    () => admins.filter((admin) => !removedIds.has(admin.player_id)),
    [admins, removedIds]
  );

  const roleCounts = useMemo(() => {
    const counts = new Map(adminGroups.map((role) => [role, 0]));
    activeAdmins.forEach((admin) => {
      const role = normalizeRole(admin.role);
      counts.set(role, (counts.get(role) ?? 0) + 1);
    });
    return counts;
  }, [activeAdmins, adminGroups]);

  const filteredAdmins = useMemo(() => {
    const needle = searched.trim().toLowerCase();
    return admins.filter((admin) => {
      const matchesSearch =
        !needle ||
        admin.name.toLowerCase().includes(needle) ||
        admin.player_id.toLowerCase().includes(needle);
      const matchesRole =
        roleFilter === "all" || normalizeRole(admin.role) === roleFilter;
      return matchesSearch && matchesRole;
    });
  }, [admins, searched, roleFilter]);

  const isValidAdminInput =
    newAdmin.name.trim() &&
    newAdmin.player_id.trim() &&
    adminGroups.includes(normalizeRole(newAdmin.role));

  const handleAddItem = () => {
    if (!isValidAdminInput) return;
    const admin = {
      player_id: newAdmin.player_id.trim(),
      name: newAdmin.name.trim(),
      role: normalizeRole(newAdmin.role),
    };

    setAdmins((previous) => {
      const existingIndex = previous.findIndex(
        (item) => item.player_id === admin.player_id
      );
      if (existingIndex < 0) return [admin, ...previous];

      return previous.map((item, index) =>
        index === existingIndex ? { ...item, ...admin } : item
      );
    });
    setRemovedIds((previous) => {
      const next = new Set(previous);
      next.delete(admin.player_id);
      return next;
    });
    setNewAdmin(initialAdmin);
  };

  const handleRoleChange = (playerId, role) => {
    setAdmins((previous) =>
      previous.map((admin) =>
        admin.player_id === playerId
          ? { ...admin, role: normalizeRole(role) }
          : admin
      )
    );
    setEditingRoleId(null);
  };

  const handleToggleRemoval = (playerId) => {
    if (!serverAdminMap.has(playerId)) {
      setAdmins((previous) =>
        previous.filter((admin) => admin.player_id !== playerId)
      );
      setChecked((previous) => {
        const next = new Set(previous);
        next.delete(playerId);
        return next;
      });
      return;
    }

    setRemovedIds((previous) => {
      const next = new Set(previous);
      if (next.has(playerId)) next.delete(playerId);
      else next.add(playerId);
      return next;
    });
  };

  const handleDeleteSelectedItems = () => {
    const selected = new Set(checked);
    setAdmins((previous) =>
      previous.filter(
        (admin) =>
          serverAdminMap.has(admin.player_id) || !selected.has(admin.player_id)
      )
    );
    setRemovedIds((previous) => {
      const next = new Set(previous);
      selected.forEach((playerId) => {
        if (serverAdminMap.has(playerId)) next.add(playerId);
      });
      return next;
    });
    setChecked(new Set());
  };

  const handleToggleSelectAll = (event) => {
    if (event.target.checked) {
      setChecked(new Set(filteredAdmins.map((admin) => admin.player_id)));
    } else {
      setChecked(new Set());
    }
  };

  const handleToggle = (playerId) => {
    setChecked((previous) => {
      const next = new Set(previous);
      if (next.has(playerId)) next.delete(playerId);
      else next.add(playerId);
      return next;
    });
  };

  const handleDiscard = () => {
    setAdmins(serverAdmins);
    setRemovedIds(new Set());
    setChecked(new Set());
    setNewAdmin(initialAdmin);
    setEditingRoleId(null);
  };

  const buildPayload = () => {
    const deletions = [];
    const additions = [];
    const draftMap = new Map(admins.map((admin) => [admin.player_id, admin]));

    serverAdmins.forEach((serverAdmin) => {
      const draftAdmin = draftMap.get(serverAdmin.player_id);
      const roleChanged =
        draftAdmin &&
        normalizeRole(serverAdmin.role) !== normalizeRole(draftAdmin.role);

      if (!draftAdmin || removedIds.has(serverAdmin.player_id) || roleChanged) {
        deletions.push({ intent: INTENT.DELETE_ADMIN, admin: serverAdmin });
      }

      if (draftAdmin && !removedIds.has(serverAdmin.player_id) && roleChanged) {
        additions.push({ intent: INTENT.ADD_ADMIN, admin: draftAdmin });
      }
    });

    admins.forEach((admin) => {
      if (
        !serverAdminMap.has(admin.player_id) &&
        !removedIds.has(admin.player_id)
      ) {
        additions.push({ intent: INTENT.ADD_ADMIN, admin });
      }
    });

    return [...deletions, ...additions];
  };

  const submitChanges = () => {
    const payload = buildPayload();
    if (!payload.length) return;
    submit(payload, { method: "POST", encType: "application/json" });
    setSaveConfirmOpen(false);
  };

  const handleSaveRequest = () => {
    if (changes.removed > 0) setSaveConfirmOpen(true);
    else submitChanges();
  };

  const handleFileUpload = (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    setToolsAnchor(null);
    if (!file) return;

    const reader = new FileReader();
    reader.onload = ({ target }) => {
      const validRows = [];
      const invalidRows = [];

      String(target?.result ?? "")
        .split(/\r?\n/)
        .forEach((row, index) => {
          if (!row.trim()) return;
          const [id, name, rawRole] = row
            .split("\t")
            .map((value) => value?.trim());
          const role = normalizeRole(rawRole);
          if (!id || !name || !adminGroups.includes(role)) {
            invalidRows.push({ line: index + 1, row });
            return;
          }
          validRows.push({ player_id: id, name, role });
        });

      setImportMode("merge");
      setImportPreview({ fileName: file.name, validRows, invalidRows });
    };
    reader.readAsText(file);
  };

  const applyImport = () => {
    if (!importPreview?.validRows.length) return;
    const importedMap = new Map(
      importPreview.validRows.map((admin) => [admin.player_id, admin])
    );

    if (importMode === "replace") {
      const imported = [...importedMap.values()];
      setAdmins(imported);
      setRemovedIds(
        new Set(
          serverAdmins
            .filter((admin) => !importedMap.has(admin.player_id))
            .map((admin) => admin.player_id)
        )
      );
    } else {
      setAdmins((previous) => {
        const merged = new Map(
          previous.map((admin) => [admin.player_id, admin])
        );
        importedMap.forEach((admin, playerId) => merged.set(playerId, admin));
        return [...merged.values()];
      });
      setRemovedIds((previous) => {
        const next = new Set(previous);
        importedMap.forEach((_, playerId) => next.delete(playerId));
        return next;
      });
    }

    setImportPreview(null);
  };

  const handleFileDownload = () => {
    const rows = activeAdmins.map((admin) => [
      `${admin.player_id}\t${admin.name}\t${normalizeRole(admin.role)}`,
    ]);
    exportFile(rows, "console-admins");
    setToolsAnchor(null);
  };

  const renderChangeStatus = (admin) => {
    const type = changeTypeFor(admin);
    const original = serverAdminMap.get(admin.player_id);

    if (type === "added") {
      return (
        <Box>
          <Typography variant="caption" color="success.main" fontWeight={800}>
            {t("settings.consoleAdmins.statusAdded")}
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block">
            {t("settings.consoleAdmins.statusAddedHint")}
          </Typography>
        </Box>
      );
    }

    if (type === "role") {
      return (
        <Box>
          <Typography variant="caption" color="warning.main" fontWeight={800}>
            {t("settings.consoleAdmins.statusRoleChanged")}
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block">
            {t("settings.consoleAdmins.statusRoleChangedHint", {
              from: roleLabel(original?.role),
              to: roleLabel(admin.role),
            })}
          </Typography>
        </Box>
      );
    }

    if (type === "removed") {
      return (
        <Box>
          <Typography variant="caption" color="error.main" fontWeight={800}>
            {t("settings.consoleAdmins.statusRemoved")}
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block">
            {t("settings.consoleAdmins.statusRemovedHint")}
          </Typography>
        </Box>
      );
    }

    return (
      <Box>
        <Typography variant="caption" color="text.secondary">
          {t("settings.consoleAdmins.statusActive")}
        </Typography>
      </Box>
    );
  };

  const getRowAccent = (admin) => {
    const type = changeTypeFor(admin);
    if (type === "added") return "success.main";
    if (type === "role") return "warning.main";
    if (type === "removed") return "error.main";
    return "transparent";
  };

  const renderRole = (admin) => {
    const isEditing = editingRoleId === admin.player_id;

    if (isEditing) {
      return (
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel id={`role-${admin.player_id}`}>
            {t("settings.consoleAdmins.role")}
          </InputLabel>
          <Select
            autoFocus
            labelId={`role-${admin.player_id}`}
            value={normalizeRole(admin.role)}
            label={t("settings.consoleAdmins.role")}
            onChange={(event) => {
              handleRoleChange(admin.player_id, event.target.value);
              setEditingRoleId(null);
            }}
          >
            {adminGroups.map((role) => (
              <MenuItem value={role} key={role}>
                {roleLabel(role)}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      );
    }

    return <RoleBadge role={admin.role} label={roleLabel(admin.role)} />;
  };

  const renderRowActions = (admin, compact = false) => {
    const removed = removedIds.has(admin.player_id);
    return (
      <Stack direction="row" spacing={0.25} justifyContent="flex-end">
        {!compact && (
          <Tooltip
            title={t("settings.consoleAdmins.openProfile", {
              name: admin.name,
            })}
          >
            <IconButton
              onClick={() => openWithId(admin.player_id)}
              aria-label={t("settings.consoleAdmins.openProfile", {
                name: admin.name,
              })}
              sx={{ minWidth: 44, minHeight: 44 }}
            >
              <PersonOutlineIcon />
            </IconButton>
          </Tooltip>
        )}
        {!removed && (
          <Tooltip
            title={t("settings.consoleAdmins.editRole", { name: admin.name })}
          >
            <IconButton
              onClick={() => setEditingRoleId(admin.player_id)}
              aria-label={t("settings.consoleAdmins.editRole", {
                name: admin.name,
              })}
              sx={{ minWidth: 44, minHeight: 44 }}
            >
              <EditOutlinedIcon />
            </IconButton>
          </Tooltip>
        )}
        <Tooltip
          title={
            removed
              ? t("settings.consoleAdmins.undoRemoval", { name: admin.name })
              : t("settings.consoleAdmins.removeAdmin", { name: admin.name })
          }
        >
          <IconButton
            onClick={() => handleToggleRemoval(admin.player_id)}
            aria-label={
              removed
                ? t("settings.consoleAdmins.undoRemoval", { name: admin.name })
                : t("settings.consoleAdmins.removeAdmin", { name: admin.name })
            }
            color={removed ? "warning" : "error"}
            sx={{ minWidth: 44, minHeight: 44 }}
          >
            {removed ? <ReplayIcon /> : <DeleteOutlineIcon />}
          </IconButton>
        </Tooltip>
      </Stack>
    );
  };

  const allVisibleChecked =
    filteredAdmins.length > 0 &&
    filteredAdmins.every((admin) => checked.has(admin.player_id));
  const someVisibleChecked =
    filteredAdmins.some((admin) => checked.has(admin.player_id)) &&
    !allVisibleChecked;

  return (
    <Box sx={{ width: "100%", minWidth: 0 }}>
      <PageHeader
        eyebrow={t("settings.consoleAdmins.register")}
        title={t("settings.consoleAdmins.title")}
        subtitle={t("settings.consoleAdmins.subtitle")}
        actions={
          <SectionSurface
            aria-label={t("settings.consoleAdmins.summary")}
            sx={{ px: 1, py: 1.25 }}
          >
            <Stack
              direction="row"
              divider={<Divider orientation="vertical" flexItem />}
            >
              <SummaryItem
                label={t("settings.consoleAdmins.total")}
                value={activeAdmins.length}
              />
              {adminGroups.slice(0, 3).map((role) => (
                <SummaryItem
                  key={role}
                  label={roleLabel(role)}
                  value={roleCounts.get(role) ?? 0}
                  role={role}
                />
              ))}
            </Stack>
          </SectionSurface>
        }
      />

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            lg: "minmax(280px, 320px) minmax(0, 1fr)",
          },
          gap: 1,
          alignItems: "start",
        }}
      >
        <SectionSurface>
          <Button
            onClick={() => setAddPanelOpen((open) => !open)}
            aria-expanded={!isMobile || addPanelOpen}
            fullWidth
            endIcon={<KeyboardArrowDownIcon />}
            sx={{
              minHeight: 48,
              justifyContent: "space-between",
              px: 1.5,
              borderBottom: "1px solid",
              borderColor: "divider",
              color: "text.primary",
              pointerEvents: { md: "none" },
              "& .MuiButton-endIcon": { display: { md: "none" } },
            }}
          >
            {t("settings.consoleAdmins.addTitle")}
          </Button>
          <Collapse in={!isMobile || addPanelOpen} timeout="auto">
            <Stack spacing={2} sx={{ p: 1.5 }}>
              <Box>
                <Typography variant="overline" color="text.secondary">
                  {t("settings.consoleAdmins.stepSearch")}
                </Typography>
                <PlayerAutocompletion
                  player={newAdmin}
                  setPlayer={setNewAdmin}
                />
                <FormHelperText>
                  {t("settings.consoleAdmins.searchHelp")}
                </FormHelperText>
              </Box>

              <Box>
                <Typography variant="overline" color="text.secondary">
                  {t("settings.consoleAdmins.stepId")}
                </Typography>
                <TextField
                  fullWidth
                  autoComplete="off"
                  value={newAdmin.player_id}
                  onChange={(event) =>
                    setNewAdmin((previous) => ({
                      ...previous,
                      player_id: event.target.value,
                    }))
                  }
                  label={t("settings.consoleAdmins.steamId")}
                />
                <FormHelperText>
                  {t("settings.consoleAdmins.idHelp")}
                </FormHelperText>
              </Box>

              <Box>
                <Typography variant="overline" color="text.secondary">
                  {t("settings.consoleAdmins.stepRole")}
                </Typography>
                <Stack spacing={0.75}>
                  {adminGroups.map((role) => {
                    const selected = normalizeRole(newAdmin.role) === role;
                    return (
                      <Button
                        key={role}
                        variant="outlined"
                        color={getRoleColor(role)}
                        onClick={() =>
                          setNewAdmin((previous) => ({ ...previous, role }))
                        }
                        aria-pressed={selected}
                        startIcon={<RoleIcon role={role} />}
                        sx={{
                          minHeight: 52,
                          justifyContent: "flex-start",
                          textAlign: "left",
                          bgcolor: selected
                            ? (currentTheme) =>
                                alpha(
                                  currentTheme.palette[getRoleColor(role)].main,
                                  0.1
                                )
                            : "transparent",
                        }}
                      >
                        <Box>
                          <Typography variant="body2" fontWeight={800}>
                            {roleLabel(role)}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {roleDescription(role)}
                          </Typography>
                        </Box>
                      </Button>
                    );
                  })}
                </Stack>
                <FormHelperText>
                  {t("settings.consoleAdmins.roleHelp")}
                </FormHelperText>
              </Box>

              <Button
                variant="contained"
                startIcon={<AddIcon />}
                disabled={!isValidAdminInput}
                onClick={handleAddItem}
                sx={{ minHeight: 44 }}
              >
                {t("settings.consoleAdmins.addToDraft")}
              </Button>
            </Stack>
          </Collapse>
        </SectionSurface>

        <SectionSurface sx={{ minWidth: 0 }}>
          <Stack
            direction={{ xs: "column", md: "row" }}
            alignItems={{ xs: "stretch", md: "center" }}
            spacing={1}
            sx={{ p: 1, borderBottom: "1px solid", borderColor: "divider" }}
          >
            <Box
              sx={{
                flex: { xs: "0 0 auto", md: "1 1 320px" },
                minWidth: 0,
                border: "1px solid",
                borderColor: "divider",
              }}
            >
              <SearchInput
                value={searched}
                onChange={(event) => setSearched(event.target.value)}
                onClear={searched ? () => setSearched("") : undefined}
                placeholder={t("settings.consoleAdmins.searchPlaceholder")}
              />
            </Box>
            <FormControl size="small" sx={{ minWidth: { md: 150 } }}>
              <InputLabel id="console-admin-role-filter">
                {t("settings.consoleAdmins.role")}
              </InputLabel>
              <Select
                labelId="console-admin-role-filter"
                value={roleFilter}
                label={t("settings.consoleAdmins.role")}
                onChange={(event) => setRoleFilter(event.target.value)}
              >
                <MenuItem value="all">
                  {t("settings.consoleAdmins.allRoles")}
                </MenuItem>
                {adminGroups.map((role) => (
                  <MenuItem value={role} key={role}>
                    {roleLabel(role)}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Typography variant="caption" color="text.secondary" noWrap>
              {t("settings.consoleAdmins.resultCount", {
                count: filteredAdmins.length,
              })}
            </Typography>
            {checked.size > 0 && (
              <Button
                variant="outlined"
                color="error"
                onClick={handleDeleteSelectedItems}
                startIcon={<DeleteOutlineIcon />}
                sx={{ minHeight: 40, whiteSpace: "nowrap" }}
              >
                {t("settings.consoleAdmins.removeSelected", {
                  count: checked.size,
                })}
              </Button>
            )}
            <Button
              variant="outlined"
              color="secondary"
              startIcon={<ImportExportOutlinedIcon />}
              endIcon={<KeyboardArrowDownIcon />}
              onClick={(event) => setToolsAnchor(event.currentTarget)}
              aria-haspopup="menu"
              aria-expanded={Boolean(toolsAnchor)}
              sx={{ minHeight: 40, whiteSpace: "nowrap" }}
            >
              {t("settings.consoleAdmins.importExport")}
            </Button>
            <Menu
              anchorEl={toolsAnchor}
              open={Boolean(toolsAnchor)}
              onClose={() => setToolsAnchor(null)}
            >
              <MenuItem component="label">
                <UploadFileOutlinedIcon fontSize="small" sx={{ mr: 1 }} />
                {t("settings.consoleAdmins.importFile")}
                <input
                  hidden
                  type="file"
                  accept=".txt,.tsv,text/plain,text/tab-separated-values"
                  onChange={handleFileUpload}
                />
              </MenuItem>
              <MenuItem onClick={handleFileDownload}>
                <DownloadOutlinedIcon fontSize="small" sx={{ mr: 1 }} />
                {t("settings.consoleAdmins.exportFile")}
              </MenuItem>
            </Menu>
          </Stack>

          <TableContainer sx={{ display: { xs: "none", md: "block" } }}>
            <Table aria-label={t("settings.consoleAdmins.tableLabel")}>
              <TableHead>
                <TableRow>
                  <TableCell padding="checkbox">
                    <Checkbox
                      checked={allVisibleChecked}
                      indeterminate={someVisibleChecked}
                      onChange={handleToggleSelectAll}
                      inputProps={{
                        "aria-label": t("settings.consoleAdmins.selectAll"),
                      }}
                    />
                  </TableCell>
                  <TableCell>{t("settings.consoleAdmins.player")}</TableCell>
                  <TableCell>{t("settings.consoleAdmins.steamId")}</TableCell>
                  <TableCell>{t("settings.consoleAdmins.role")}</TableCell>
                  <TableCell>
                    {t("settings.consoleAdmins.changeStatus")}
                  </TableCell>
                  <TableCell align="right">{t("common.actions")}</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredAdmins.map((admin) => {
                  const removed = removedIds.has(admin.player_id);
                  const changeType = changeTypeFor(admin);
                  const selectionColor =
                    changeType === "added"
                      ? "success"
                      : changeType === "removed"
                      ? "error"
                      : "warning";
                  return (
                    <TableRow
                      key={admin.player_id}
                      selected={checked.has(admin.player_id)}
                      sx={{
                        opacity: removed ? 0.68 : 1,
                        bgcolor: removed
                          ? (currentTheme) =>
                              alpha(currentTheme.palette.error.main, 0.04)
                          : undefined,
                        "&.Mui-selected, &.Mui-selected:hover": {
                          bgcolor: (currentTheme) =>
                            alpha(
                              currentTheme.palette[selectionColor].main,
                              0.07
                            ),
                        },
                        "& > *:first-of-type": {
                          borderLeft: "3px solid",
                          borderLeftColor: getRowAccent(admin),
                        },
                      }}
                    >
                      <TableCell padding="checkbox">
                        <Checkbox
                          checked={checked.has(admin.player_id)}
                          onChange={() => handleToggle(admin.player_id)}
                          inputProps={{
                            "aria-label": t(
                              "settings.consoleAdmins.selectAdmin",
                              {
                                name: admin.name,
                              }
                            ),
                          }}
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" fontWeight={700}>
                          {admin.name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{ fontFamily: "monospace" }}
                        >
                          {admin.player_id}
                        </Typography>
                      </TableCell>
                      <TableCell>{renderRole(admin)}</TableCell>
                      <TableCell>{renderChangeStatus(admin)}</TableCell>
                      <TableCell align="right">
                        {renderRowActions(admin)}
                      </TableCell>
                    </TableRow>
                  );
                })}
                {!filteredAdmins.length && (
                  <TableRow>
                    <TableCell colSpan={6}>
                      <Box sx={{ py: 5, textAlign: "center" }}>
                        <AdminPanelSettingsOutlinedIcon
                          sx={{ color: "text.disabled" }}
                        />
                        <Typography sx={{ mt: 1 }}>
                          {admins.length
                            ? t("settings.consoleAdmins.noResults")
                            : t("settings.consoleAdmins.noAdmins")}
                        </Typography>
                      </Box>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>

          <Stack
            sx={{ display: { xs: "flex", md: "none" } }}
            divider={<Divider />}
          >
            {filteredAdmins.map((admin) => {
              const removed = removedIds.has(admin.player_id);
              return (
                <Box
                  key={admin.player_id}
                  sx={{
                    p: 1.25,
                    borderLeft: "3px solid",
                    borderLeftColor: getRowAccent(admin),
                    opacity: removed ? 0.68 : 1,
                  }}
                >
                  <Stack direction="row" alignItems="flex-start" spacing={1}>
                    <Checkbox
                      checked={checked.has(admin.player_id)}
                      onChange={() => handleToggle(admin.player_id)}
                      inputProps={{
                        "aria-label": t("settings.consoleAdmins.selectAdmin", {
                          name: admin.name,
                        }),
                      }}
                    />
                    <Box sx={{ minWidth: 0, flex: 1 }}>
                      <Typography fontWeight={700}>{admin.name}</Typography>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ fontFamily: "monospace", wordBreak: "break-all" }}
                      >
                        {admin.player_id}
                      </Typography>
                      <Stack spacing={0.75} sx={{ mt: 1 }}>
                        {renderRole(admin)}
                        {renderChangeStatus(admin)}
                      </Stack>
                    </Box>
                    {renderRowActions(admin, true)}
                  </Stack>
                </Box>
              );
            })}
            {!filteredAdmins.length && (
              <Box sx={{ p: 4, textAlign: "center" }}>
                <Typography>
                  {admins.length
                    ? t("settings.consoleAdmins.noResults")
                    : t("settings.consoleAdmins.noAdmins")}
                </Typography>
              </Box>
            )}
          </Stack>
        </SectionSurface>
      </Box>

      <ConfigActionBar
        mobileSticky={hasChanges}
        dirty={hasChanges}
        dirtyLabel={
          hasChanges
            ? t("settings.consoleAdmins.pendingChanges", {
                count: totalChanges,
              })
            : undefined
        }
        stateLabel={
          hasChanges
            ? t("settings.consoleAdmins.changeSummary", changes)
            : t("settings.consoleAdmins.allSaved")
        }
        stateDescription={
          hasChanges
            ? t("settings.consoleAdmins.reviewBeforeSave")
            : t("settings.consoleAdmins.allSavedHint")
        }
        stateIcon={
          hasChanges ? (
            <WarningAmberOutlinedIcon color="warning" />
          ) : (
            <SaveOutlinedIcon color="success" />
          )
        }
        secondaryActions={[
          {
            id: "discard-console-admins",
            label: t("settings.consoleAdmins.discard"),
            onClick: handleDiscard,
            disabled: !hasChanges || isSaving,
            startIcon: <ReplayIcon />,
          },
        ]}
        primaryAction={{
          label: t("settings.consoleAdmins.saveChanges"),
          loadingLabel: t("settings.consoleAdmins.savingChanges"),
          onClick: handleSaveRequest,
          disabled: !hasChanges,
          loading: isSaving,
          startIcon: <SaveOutlinedIcon />,
        }}
      />

      <Dialog
        open={Boolean(importPreview)}
        onClose={() => setImportPreview(null)}
        fullWidth
        maxWidth="sm"
        aria-labelledby="console-admin-import-title"
      >
        <DialogTitle id="console-admin-import-title">
          {t("settings.consoleAdmins.importPreviewTitle")}
        </DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 0.5 }}>
            <Typography color="text.secondary">
              {t("settings.consoleAdmins.importPreviewDescription", {
                file: importPreview?.fileName,
                valid: importPreview?.validRows.length ?? 0,
                invalid: importPreview?.invalidRows.length ?? 0,
              })}
            </Typography>
            {(importPreview?.invalidRows.length ?? 0) > 0 && (
              <Alert severity="warning">
                {t("settings.consoleAdmins.invalidImportRows", {
                  count: importPreview.invalidRows.length,
                  lines: importPreview.invalidRows
                    .slice(0, 8)
                    .map((row) => row.line)
                    .join(", "),
                })}
              </Alert>
            )}
            <RadioGroup
              value={importMode}
              onChange={(event) => setImportMode(event.target.value)}
            >
              <FormControlLabel
                value="merge"
                control={<Radio />}
                label={t("settings.consoleAdmins.importMerge")}
              />
              <FormControlLabel
                value="replace"
                control={<Radio />}
                label={t("settings.consoleAdmins.importReplace")}
              />
            </RadioGroup>
            {importMode === "replace" && (
              <Alert severity="error">
                {t("settings.consoleAdmins.importReplaceWarning")}
              </Alert>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setImportPreview(null)}>
            {t("common.cancel")}
          </Button>
          <Button
            variant="contained"
            onClick={applyImport}
            disabled={!importPreview?.validRows.length}
          >
            {t("settings.consoleAdmins.applyImport")}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={saveConfirmOpen}
        onClose={() => setSaveConfirmOpen(false)}
        aria-labelledby="console-admin-save-title"
      >
        <DialogTitle id="console-admin-save-title">
          {t("settings.consoleAdmins.confirmSaveTitle")}
        </DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            {t("settings.consoleAdmins.confirmSaveDescription", changes)}
          </Alert>
          <Typography color="text.secondary">
            {t("settings.consoleAdmins.confirmSaveHint")}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSaveConfirmOpen(false)}>
            {t("common.cancel")}
          </Button>
          <Button variant="contained" color="error" onClick={submitChanges}>
            {t("settings.consoleAdmins.confirmSave")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
