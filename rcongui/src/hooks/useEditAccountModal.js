import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { cmd } from "@/utils/fetchUtils";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Button from "@mui/material/Button";
import { Stack, Alert, CircularProgress, FormControlLabel, Switch } from "@mui/material";
import CheckIcon from "@mui/icons-material/Check";
import ErrorIcon from "@mui/icons-material/Error";
import { ControlledTextInput } from "@/components/form/core/ControlledTextInput";
import { Autocomplete } from "@mui/material";
import countries from "country-list";
import { CountryFlag } from "@/components/shared/CountryFlag";
import ISO6391 from 'iso-639-1';
import { useTranslation } from "react-i18next";
import { accountCopy } from "./edit-account-copy";

// Get all countries for autocomplete
const countryOptions = countries.getCodes().map((code) => ({
  code: code,
  name: countries.getName(code),
}));

// Get all languages for autocomplete
const languageOptions = ISO6391.getLanguages(ISO6391.getAllCodes()).map((lang) => ({
  code: lang.code,
  name: lang.name,
  nativeName: lang.nativeName,
}));

export function useEditAccountModal(playerId, currentAccountData) {
  const { i18n } = useTranslation();
  const language = i18n.resolvedLanguage || "en";
  const c = accountCopy(language);
  const regions = new Intl.DisplayNames([language], { type: "region" });
  const languages = new Intl.DisplayNames([language], { type: "language" });
  const [open, setOpen] = useState(false);
  const [submitStatus, setSubmitStatus] = useState(null); // null, 'success', 'error'
  const [errorMessage, setErrorMessage] = useState("");
  const [selectedCountry, setSelectedCountry] = useState(
    currentAccountData?.country || ""
  );
  const [selectedLanguage, setSelectedLanguage] = useState(
    currentAccountData?.lang || "en"
  );
  const queryClient = useQueryClient();

  const {
    control,
    handleSubmit,
    formState: { errors },
    reset,
    setValue,
    watch,
    ...formProps
  } = useForm({
    defaultValues: {
      name: currentAccountData?.name || "",
      discord_id: currentAccountData?.discord_id || "",
      is_member: currentAccountData?.is_member || false,
      country: currentAccountData?.country?.toUpperCase() || "",
      lang: currentAccountData?.lang || "en",
    },
  });

  // Watch the country and language fields to sync with local state
  const watchedCountry = watch("country");
  const watchedLanguage = watch("lang");

  React.useEffect(() => {
    setSelectedCountry(watchedCountry || "");
  }, [watchedCountry]);

  React.useEffect(() => {
    setSelectedLanguage(watchedLanguage || "en");
  }, [watchedLanguage]);

  const { mutate: editPlayerAccount, isPending } = useMutation({
    mutationFn: async (data) => {
      // Convert empty strings to null and ensure proper types
      const payload = {
        player_id: playerId,
        name: data.name || null,
        discord_id: data.discord_id || null,
        is_member: Boolean(data.is_member),
        country: data.country || null,
        lang: data.lang || "en",
      };

      return cmd.EDIT_PLAYER_ACCOUNT({
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
      setErrorMessage(error.message || c.failed);
    },
  });

  const openModal = () => {
    setOpen(true);
    setSubmitStatus(null);
    setErrorMessage("");
    // Reset form with current values
    const currentValues = {
      name: currentAccountData?.name || "",
      discord_id: currentAccountData?.discord_id || "",
      is_member: currentAccountData?.is_member || false,
      country: currentAccountData?.country || "",
      lang: currentAccountData?.lang || "en",
    };
    reset(currentValues);
    setSelectedCountry(currentValues.country);
    setSelectedLanguage(currentValues.lang);
  };

  const closeModal = () => {
    setOpen(false);
    setSubmitStatus(null);
    setErrorMessage("");
    reset();
  };

  const onSubmit = (data) => {
    setSubmitStatus(null);
    setErrorMessage("");
    editPlayerAccount(data);
  };

  const modal = (
    <Dialog
      open={open}
      onClose={closeModal}
      slotProps={{
        paper: {
          component: "form",
          onSubmit: handleSubmit(onSubmit),
        },
      }}
    >
      <DialogTitle>{c.title}</DialogTitle>
      <DialogContent>
        <DialogContentText>
          {c.description}
        </DialogContentText>

        {submitStatus === 'success' && (
          <Alert severity="success" sx={{ mt: 2 }}>
            <CheckIcon sx={{ mr: 1 }} />
            {c.success}
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
            control={control}
            name="name"
            label={c.accountName}
            rules={{
              pattern: {
                value: /^[a-zA-Z0-9\s\-_]+$/,
                message: c.nameRule
              }
            }}
            helperText={c.nameHelp}
            fullWidth
          />

          <ControlledTextInput
            control={control}
            name="discord_id"
            label="Discord ID"
            rules={{
              pattern: {
                value: /^\d+$/,
                message: c.discordRule
              }
            }}
            helperText={c.discordHelp}
            fullWidth
          />

          <FormControlLabel
            control={
              <Switch
                checked={watch("is_member")}
                onChange={(e) => setValue("is_member", e.target.checked)}
                disabled={isPending}
              />
            }
            label={c.member}
          />

          <Autocomplete
            options={countryOptions}
            getOptionLabel={(option) => regions.of(option.code) || option.name}
            value={
              countryOptions.find((c) => c.code.toUpperCase() === selectedCountry.toUpperCase()) || null
            }
            onChange={(event, newValue) => {
              const countryCode = newValue?.code?.toUpperCase() || "";
              setSelectedCountry(countryCode);
              setValue("country", countryCode, { shouldValidate: true });
            }}
            disabled={isPending}
            renderOption={({ key, ...props }, option) => (
              <li key={key} {...props}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <CountryFlag country={option.code} />
                  <span>{regions.of(option.code) || option.name}</span>
                </Stack>
              </li>
            )}
            renderInput={(params) => (
              <ControlledTextInput
                {...params}
                control={control}
                name="country"
                label={c.country}
                helperText={errors.country ? errors.country.message : c.countryHelp}
                fullWidth
              />
            )}
          />

          <Autocomplete
            options={languageOptions}
            getOptionLabel={(option) => `${languages.of(option.code) || option.name} (${option.nativeName})`}
            value={
              languageOptions.find((l) => l.code === selectedLanguage) ||
              languageOptions.find((l) => l.code === "en") || null
            }
            onChange={(event, newValue) => {
              const languageCode = newValue?.code || "en";
              setSelectedLanguage(languageCode);
              setValue("lang", languageCode, { shouldValidate: true });
            }}
            disabled={isPending}
            renderOption={({ key, ...props }, option) => (
              <li key={key} {...props}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <span>{languages.of(option.code) || option.name}</span>
                  <span style={{ opacity: 0.7 }}>({option.nativeName})</span>
                </Stack>
              </li>
            )}
            renderInput={(params) => (
              <ControlledTextInput
                {...params}
                control={control}
                name="lang"
                label={c.language}
                rules={{
                  pattern: {
                    value: /^[a-z]{2}$/,
                    message: c.languageRule
                  }
                }}
                helperText={c.languageHelp}
                fullWidth
              />
            )}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={closeModal} disabled={isPending}>
          {c.cancel}
        </Button>
        <Button
          type="submit"
          disabled={isPending}
          startIcon={isPending ? <CircularProgress size={16} /> : null}
        >
          {isPending ? c.updating : c.update}
        </Button>
      </DialogActions>
    </Dialog>
  );

  return {
    modal,
    openModal,
    isPending,
  };
}
