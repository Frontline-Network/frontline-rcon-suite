import React from "react";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Chip from "@mui/material/Chip";
import { Stack, Alert, CircularProgress } from "@mui/material";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { cmd } from "@/utils/fetchUtils";
import CheckIcon from "@mui/icons-material/Check";
import ErrorIcon from "@mui/icons-material/Error";
import { ControlledTextInput } from "@/components/form/core/ControlledTextInput";
import { ControlledSelect } from "@/components/form/core/ControlledSelect";
import { useTranslation } from "react-i18next";
import { getPlatformOptions } from "@/constants/platforms";

function EditSoldierButton({ Icon, playerId, currentSoldierData }) {
  const { t } = useTranslation();
  const [open, setOpen] = React.useState(false);
  const [submitStatus, setSubmitStatus] = React.useState(null); // null, 'success', 'error'
  const [errorMessage, setErrorMessage] = React.useState("");
  const queryClient = useQueryClient();

  const platformOptions = getPlatformOptions(currentSoldierData?.platform);

  const {
    control,
    handleSubmit,
    formState: { errors },
    reset,
    ...formProps
  } = useForm({
    defaultValues: {
      name: currentSoldierData?.name || "",
      level: currentSoldierData?.level || "",
      platform: currentSoldierData?.platform || "",
      clan_tag: currentSoldierData?.clan_tag || "",
      eos_id: currentSoldierData?.eos_id || "",
    },
  });

  const { mutate: editPlayerSoldier, isPending } = useMutation({
    mutationFn: async (data) => {
      // Convert empty strings to null and level to number
      const payload = {
        player_id: playerId,
        name: data.name || null,
        level: data.level ? parseInt(data.level, 10) : null,
        platform: data.platform || null,
        clan_tag: data.clan_tag || null,
        eos_id: data.eos_id || null,
      };
      
      return cmd.EDIT_PLAYER_SOLDIER({
        payload,
        throwRouteError: false,
      });
    },
    onSuccess: (data) => {
      setSubmitStatus('success');
      // Invalidate and refetch player profile data
      queryClient.invalidateQueries({ queryKey: ['player-profile', playerId] });
      // Close dialog after a short delay
      setTimeout(() => {
        setOpen(false);
        setSubmitStatus(null);
        reset();
      }, 2000);
    },
    onError: (error) => {
      setSubmitStatus('error');
      setErrorMessage(error.message || t("playerEditor.soldier.failed"));
    },
  });

  const handleClickOpen = () => {
    setOpen(true);
    setSubmitStatus(null);
    setErrorMessage("");
    // Reset form with current values
    reset({
      name: currentSoldierData?.name || "",
      level: currentSoldierData?.level || "",
      platform: currentSoldierData?.platform || "",
      clan_tag: currentSoldierData?.clan_tag || "",
      eos_id: currentSoldierData?.eos_id || "",
    });
  };

  const handleClose = () => {
    setOpen(false);
    setSubmitStatus(null);
    setErrorMessage("");
    reset();
  };

  const onSubmit = (data) => {
    setSubmitStatus(null);
    setErrorMessage("");
    editPlayerSoldier(data);
  };

  // Check if fields should be disabled
  const isNameDisabled = currentSoldierData?.name && currentSoldierData.name.trim() !== "";
  const isLevelDisabled = currentSoldierData?.level && currentSoldierData.level > 0;
  const isPlatformDisabled = currentSoldierData?.platform && currentSoldierData.platform.trim() !== "";
  const isClanTagDisabled = currentSoldierData?.clan_tag !== null;
  const isEosIdDisabled = currentSoldierData?.eos_id && currentSoldierData.eos_id.trim() !== "";
  return (
    <React.Fragment>
      <Chip
        icon={<Icon />}
        label={t("playerEditor.addInformation")}
        variant="outlined"
        size="small"
        onClick={handleClickOpen}
      />
      <Dialog
        open={open}
        onClose={handleClose}
        slotProps={{
          paper: {
            component: "form",
            onSubmit: handleSubmit(onSubmit),
          },
        }}
      >
        <DialogTitle>{t("playerEditor.soldier.title")}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {t("playerEditor.soldier.description")}
          </DialogContentText>
          
          {submitStatus === 'success' && (
            <Alert severity="success" sx={{ mt: 2 }}>
              <CheckIcon sx={{ mr: 1 }} />
              {t("playerEditor.soldier.success")}
            </Alert>
          )}
          
          {submitStatus === 'error' && (
            <Alert severity="error" sx={{ mt: 2 }}>
              <ErrorIcon sx={{ mr: 1 }} />
              {errorMessage}
            </Alert>
          )}

          <Stack spacing={2} sx={{ mt: 2 }}>
            <ControlledTextInput
              error={errors.name}
              control={control}
              name="name"
              label={t("playerEditor.soldier.name")}
              disabled={isPending || isNameDisabled}
              rules={{
                pattern: {
                  value: /^[a-zA-Z0-9\s\-_]+$/,
                  message: t("playerEditor.validation.name")
                }
              }}
              helperText={
                isNameDisabled ? t("playerEditor.disabledField") : t("playerEditor.soldier.nameHelp")
              }
              fullWidth
            />
            
            <ControlledTextInput
              error={errors.level}
              control={control}
              name="level"
              label={t("playerEditor.soldier.level")}
              type="number"
              disabled={isPending || isLevelDisabled}
              rules={{
                pattern: {
                  value: /^[0-9]+$/,
                  message: t("playerEditor.validation.level")
                },
                min: {
                  value: 1,
                  message: t("playerEditor.validation.levelMin")
                },
                max: {
                  value: 500,
                  message: t("playerEditor.validation.levelMax")
                }
              }}
              helperText={
                isLevelDisabled ? t("playerEditor.disabledField") : t("playerEditor.soldier.levelHelp")
              }
              fullWidth
            />
            
            <ControlledSelect
              error={errors.platform}
              control={control}
              name="platform"
              label={t("playerEditor.soldier.platform")}
              disabled={isPending || isPlatformDisabled}
              options={platformOptions}
              rules={{
                validate: (value) => !value || platformOptions.some((option) => option.value === value) || t("playerEditor.validation.platform"),
              }}
              helperText={
                isPlatformDisabled ? t("playerEditor.disabledField") : t("playerEditor.soldier.platformHelp")
              }
            />
            
            <ControlledTextInput
              error={errors.clan_tag}
              control={control}
              name="clan_tag"
              label={t("playerEditor.soldier.clanTag")}
              disabled={isPending || isClanTagDisabled}
              rules={{
                pattern: {
                  value: /^[a-zA-Z0-9\s\-_\[\]]*$/,
                  message: t("playerEditor.validation.clanTag")
                },
                maxLength: {
                  value: 4,
                  message: t("playerEditor.validation.clanTagLength")
                }
              }}
              helperText={
                errors.clan_tag ? errors.clan_tag.message : isClanTagDisabled ? t("playerEditor.disabledField") : t("playerEditor.soldier.clanTagHelp")
              }
              fullWidth
            />

            <ControlledTextInput
              error={errors.eos_id}
              control={control}
              name="eos_id"
              label={t("playerEditor.soldier.eosId")}
              disabled={isPending || isEosIdDisabled}
              helperText={
                isEosIdDisabled ? t("playerEditor.disabledField") : t("playerEditor.soldier.eosIdHelp")
              }
              fullWidth
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose} disabled={isPending}>
            {t("common.cancel")}
          </Button>
          <Button 
            type="submit" 
            disabled={isPending || (isNameDisabled && isLevelDisabled && isPlatformDisabled && isClanTagDisabled)}
            startIcon={isPending ? <CircularProgress size={16} /> : null}
          >
            {isPending ? t("playerEditor.updating") : t("common.save")}
          </Button>
        </DialogActions>
      </Dialog>
    </React.Fragment>
  );
}

export default EditSoldierButton;
