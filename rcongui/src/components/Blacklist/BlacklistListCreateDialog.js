import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import { Checkbox, FormControl, FormControlLabel, FormGroup, InputLabel, MenuItem, Select, Switch, Typography } from '@mui/material';
import Grid from "@mui/material/Grid2";
import {Fragment, useEffect, useState} from "react";
import { useTranslation } from "react-i18next";

export const SYNC_METHODS = {
  kick_only: "Kick Only",
  ban_on_connect: "Ban On Connect",
  ban_immediately: "Ban Immediately",
}

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
  const [name, setName] = useState("");
  const [serverNumbers, setServerNumbers] = useState(null);
  const [syncMethod, setSyncMethod] = useState("");
  
  useEffect(() => {
    if (initialValues) {
      if (initialValues.name !== undefined) setName(initialValues.name);
      if (initialValues.servers !== undefined) setServerNumbers(initialValues.servers);
      if (initialValues.syncMethod !== undefined) setSyncMethod(initialValues.syncMethod);
    }
  }, [open])

  const handleClose = () => {
    setOpen(false);
    setName("");
    setServerNumbers(null);
    setSyncMethod("");
  }

  function toggleAllServers(enabled) {
    setServerNumbers(enabled ? null : Object.keys(servers).map(n => parseInt(n)));
  }

  function toggleServer(number, enabled) {
    const nums = [...serverNumbers];

    if (enabled) {
      if (!nums.includes(number)) nums.push(number);
    } else {
      const index = nums.indexOf(number);
      if (index > -1) {
        nums.splice(index, 1);
      }
    }
    setServerNumbers(nums);
  }

  return (
    (<Dialog
        open={open}
        onClose={handleClose}
        PaperProps={{
          component: 'form',
          onSubmit: (event) => {
            event.preventDefault();
            const data = {
              name,
              servers: serverNumbers,
              syncMethod,
            }
            onSubmit(data);
            handleClose();
          },
        }}
      >
      <DialogTitle>{titleText || t("records.blacklists.editList")}</DialogTitle>
      <DialogContent>
        <DialogContentText>
          {t("records.blacklists.listDescription")}
        </DialogContentText>

        <Grid container justifyContent="space-between" spacing={4}>
          <Grid size={6}>
            <TextField
              required
              id="name"
              name="name"
              label={t("records.blacklists.listName")}
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              fullWidth
              variant="standard"
            />
          </Grid>
          <Grid size={6}>
            <FormControl required fullWidth>
              <InputLabel>{t("records.blacklists.syncMethod")}</InputLabel>
              <Select
                label={t("records.blacklists.syncMethod")}
                value={syncMethod}
                onChange={(e) => setSyncMethod(e.target.value)}
              >
                {Object.keys(SYNC_METHODS).map((value) => (
                  <MenuItem key={value} value={value}>{t(`records.blacklists.syncMethods.${value}`)}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
        </Grid>
          <Typography variant="caption">
            {syncMethod ? t(`records.blacklists.syncDescriptions.${syncMethod}`) : ""}
          </Typography>
        <br/>
        <Typography variant="h6">{t("records.blacklists.servers")}</Typography>

        <Grid container alignContent="flex-start">
          <Grid size={6}>
            <FormGroup>
              {Object.entries(servers).map(([number, name]) => (
                <FormControlLabel key={number} label={name} control={
                  <Checkbox
                    checked={serverNumbers === null || serverNumbers.includes(parseInt(number))}
                    disabled={serverNumbers === null}
                    onChange={(e) => toggleServer(parseInt(number), e.target.checked)}
                  />
                }/>
              ))}
            </FormGroup>
          </Grid>
          <Grid size={6}>
            <FormControlLabel
              label={t("records.blacklists.enableAllServers")}
              control={
              <Switch
                checked={serverNumbers === null}
                onChange={(e) => toggleAllServers(e.target.checked)}
              />
            }/>
          </Grid>
        </Grid>

      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>{t("common.cancel")}</Button>
        <Button type="submit" disabled={name === "" || syncMethod === ""}>{submitText || t("common.save")}</Button>
      </DialogActions>
    </Dialog>)
  );
}

export function BlacklistListCreateButton({
  servers,
  onSubmit,
  initialValues,
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  const handleClickOpen = () => {
    setOpen(true);
  };

  return (
    <Fragment>
      <Button 
        variant="contained"
        color="primary"
        size="large"
        onClick={handleClickOpen}
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
  )
}
