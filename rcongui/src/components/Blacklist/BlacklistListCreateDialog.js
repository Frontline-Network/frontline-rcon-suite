import {
  Alert,
  Box,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  FormControl,
  FormControlLabel,
  FormGroup,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Switch,
  TextField,
  Typography,
  useMediaQuery,
} from "@mui/material";
import DnsOutlinedIcon from "@mui/icons-material/DnsOutlined";
import SaveOutlinedIcon from "@mui/icons-material/SaveOutlined";
import SyncAltIcon from "@mui/icons-material/SyncAlt";
import { Fragment, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

export const SYNC_METHODS = {
  kick_only: "Kick Only",
  ban_on_connect: "Ban On Connect",
  ban_immediately: "Ban Immediately",
};

export default function BlacklistListCreateDialog({
  open,
  setOpen,
  servers,
  onSubmit,
  initialValues,
  titleText,
  submitText,
}) {
  const { t } = useTranslation();
  const compact = useMediaQuery((theme) => theme.breakpoints.down("sm"));
  const [name, setName] = useState("");
  const [serverNumbers, setServerNumbers] = useState(null);
  const [syncMethod, setSyncMethod] = useState("");

  useEffect(() => {
    if (!open) return;
    setName(initialValues?.name ?? "");
    setServerNumbers(
      initialValues?.servers === undefined ? null : initialValues.servers
    );
    setSyncMethod(initialValues?.syncMethod ?? "");
  }, [initialValues, open]);

  const handleClose = () => {
    setOpen(false);
  };

  function toggleAllServers(enabled) {
    setServerNumbers(
      enabled ? null : Object.keys(servers).map((number) => Number(number))
    );
  }

  function toggleServer(number, enabled) {
    const numbers = [...(serverNumbers || [])];
    if (enabled && !numbers.includes(number)) numbers.push(number);
    if (!enabled) {
      const index = numbers.indexOf(number);
      if (index > -1) numbers.splice(index, 1);
    }
    setServerNumbers(numbers);
  }

  const hasUnknownSync = syncMethod && !SYNC_METHODS[syncMethod];
  const selectedServerCount =
    serverNumbers === null ? Object.keys(servers).length : serverNumbers.length;

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      fullScreen={compact}
      fullWidth
      maxWidth="md"
      PaperProps={{
        component: "form",
        onSubmit: (event) => {
          event.preventDefault();
          onSubmit({ name, servers: serverNumbers, syncMethod });
          handleClose();
        },
        sx: {
          borderRadius: 0,
          border: compact ? 0 : "1px solid",
          borderColor: "divider",
        },
      }}
    >
      <DialogTitle>{titleText || t("records.blacklists.editList")}</DialogTitle>
      <DialogContent dividers sx={{ p: { xs: 1.5, sm: 2.5 } }}>
        <DialogContentText sx={{ mb: 2 }}>
          {t("records.blacklists.listDescription")}
        </DialogContentText>

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
            gap: 1.5,
          }}
        >
          <TextField
            required
            id="blacklist-name"
            name="name"
            label={t("records.blacklists.listName")}
            type="text"
            value={name}
            onChange={(event) => setName(event.target.value)}
            fullWidth
            size="small"
          />
          <FormControl required fullWidth size="small">
            <InputLabel id="blacklist-sync-method-label">
              {t("records.blacklists.syncMethod")}
            </InputLabel>
            <Select
              labelId="blacklist-sync-method-label"
              label={t("records.blacklists.syncMethod")}
              value={syncMethod}
              onChange={(event) => setSyncMethod(event.target.value)}
            >
              {hasUnknownSync ? (
                <MenuItem value={syncMethod}>{syncMethod}</MenuItem>
              ) : null}
              {Object.keys(SYNC_METHODS).map((value) => (
                <MenuItem key={value} value={value}>
                  {t(`records.blacklists.syncMethods.${value}`)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>

        <Alert
          severity={syncMethod === "ban_immediately" ? "warning" : "info"}
          icon={<SyncAltIcon />}
          sx={{ mt: 1.5 }}
        >
          {syncMethod
            ? t(
                `records.blacklists.syncDescriptions.${syncMethod}`,
                t("records.blacklists.unknownSyncDescription")
              )
            : t("records.blacklists.syncMethod")}
        </Alert>

        <Divider sx={{ my: 2.5 }} />

        <Stack
          direction={{ xs: "column", sm: "row" }}
          spacing={1.5}
          alignItems={{ xs: "stretch", sm: "center" }}
          justifyContent="space-between"
        >
          <Box>
            <Stack direction="row" spacing={0.75} alignItems="center">
              <DnsOutlinedIcon color="primary" />
              <Typography component="h3" variant="h6">
                {t("records.blacklists.servers")}
              </Typography>
            </Stack>
            <Typography variant="caption" color="text.secondary">
              {t("records.blacklists.serverScope", {
                count: selectedServerCount,
              })}
            </Typography>
          </Box>
          <FormControlLabel
            label={t("records.blacklists.enableAllServers")}
            control={
              <Switch
                checked={serverNumbers === null}
                onChange={(event) => toggleAllServers(event.target.checked)}
              />
            }
          />
        </Stack>

        <FormGroup
          sx={{
            mt: 1.25,
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))" },
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          {Object.entries(servers).map(([number, serverName]) => (
            <FormControlLabel
              key={number}
              label={serverName}
              control={
                <Checkbox
                  checked={
                    serverNumbers === null ||
                    serverNumbers.includes(Number(number))
                  }
                  disabled={serverNumbers === null}
                  onChange={(event) =>
                    toggleServer(Number(number), event.target.checked)
                  }
                />
              }
              sx={{
                m: 0,
                minHeight: 48,
                px: 1,
                borderBottom: "1px solid",
                borderRight: { sm: "1px solid" },
                borderColor: "divider",
              }}
            />
          ))}
          {!Object.keys(servers).length ? (
            <Typography color="text.secondary" sx={{ p: 2 }}>
              {t("records.blacklists.noConnectedServers")}
            </Typography>
          ) : null}
        </FormGroup>
      </DialogContent>
      <DialogActions sx={{ p: 1.5 }}>
        <Button onClick={handleClose} color="inherit" variant="outlined">
          {t("common.cancel")}
        </Button>
        <Button
          type="submit"
          variant="contained"
          startIcon={<SaveOutlinedIcon />}
          disabled={!name.trim() || !syncMethod}
        >
          {submitText || t("common.save")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export function BlacklistListCreateButton({
  servers,
  onSubmit,
  initialValues,
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  return (
    <Fragment>
      <Button
        variant="contained"
        color="primary"
        onClick={() => setOpen(true)}
        sx={{ minHeight: 42, borderRadius: 0 }}
      >
        {t("records.blacklists.createList")}
      </Button>
      <BlacklistListCreateDialog
        open={open}
        setOpen={setOpen}
        servers={servers}
        onSubmit={onSubmit}
        initialValues={initialValues}
        titleText={t("records.blacklists.createListTitle")}
        submitText={t("records.blacklists.createList")}
      />
    </Fragment>
  );
}
