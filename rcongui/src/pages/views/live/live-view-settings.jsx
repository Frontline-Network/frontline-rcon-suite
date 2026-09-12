import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Stack,
  Switch,
  Typography,
} from "@mui/material";
import TuneOutlined from "@mui/icons-material/TuneOutlined";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/hooks/useAuth";
import { cmd } from "@/utils/fetchUtils";
import {
  DEFAULT_LIVE_CARDS,
  liveViewPreferencesKey,
  normalizeLiveViewPreferences,
} from "./live-view-preferences.mjs";

export function useLiveViewPreferences() {
  const { permissions } = useAuth();
  const userName = permissions?.user_name;
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: liveViewPreferencesKey(userName),
    queryFn: () => cmd.GET_OWN_LIVE_VIEW(),
    enabled: Boolean(userName),
    staleTime: 30_000,
    refetchOnWindowFocus: false,
    retry: 1,
  });
  const mutation = useMutation({
    mutationFn: async ({ preferences, owner }) => {
      await queryClient.cancelQueries({
        queryKey: liveViewPreferencesKey(owner),
        exact: true,
      });
      const response = await cmd.SET_OWN_LIVE_VIEW(preferences);
      return response.result;
    },
    onSuccess: (data, { owner }) => {
      queryClient.setQueryData(
        liveViewPreferencesKey(owner),
        normalizeLiveViewPreferences(data)
      );
    },
  });
  return {
    userName,
    query,
    mutation,
    preferences: normalizeLiveViewPreferences(query.data),
  };
}

const labels = {
  commander: "statusCommander",
  squad_leaders: "statusSquadLeaders",
  vips: "vips",
  watched: "watched",
  score: "score",
  next_map: "nextMap",
};

export function LiveViewSettings({ settings }) {
  const { t } = useTranslation();
  const { userName, preferences, query, mutation } = settings;
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(null);
  const selection = draft ?? preferences;
  const busy = mutation.isPending;
  const close = () => {
    if (!busy) setOpen(false);
  };
  const ready = Boolean(userName && query.isSuccess);
  return (
    <>
      <Button
        size="small"
        aria-label={t("views.live.customizeView")}
        startIcon={<TuneOutlined />}
        onClick={() => {
          setDraft(null);
          mutation.reset();
          setOpen(true);
        }}
        sx={{ flexShrink: 0, m: 0.5 }}
      >
        {t("views.live.displaySettings")}
      </Button>
      <Dialog
        open={open}
        onClose={close}
        fullWidth
        maxWidth="xs"
        aria-labelledby="live-view-settings-title"
      >
        <DialogTitle id="live-view-settings-title">
          {t("views.live.customizeView")}
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {t("views.live.personalStatusHelp")}
          </Typography>
          {query.isError ? (
            <Alert
              severity="error"
              action={
                <Button onClick={() => query.refetch()}>
                  {t("views.live.retrySettings")}
                </Button>
              }
            >
              {t("views.live.loadSettingsFailed")}
            </Alert>
          ) : null}
          {mutation.isError ? (
            <Alert severity="error">{t("views.live.saveSettingsFailed")}</Alert>
          ) : null}
          <Stack>
            {Object.keys(DEFAULT_LIVE_CARDS).map((key) => (
              <FormControlLabel
                key={key}
                label={t(`views.live.${labels[key]}`)}
                control={
                  <Switch
                    checked={selection.cards[key]}
                    disabled={!ready || busy}
                    onChange={(_, checked) =>
                      setDraft((current) => ({
                        ...(current ?? preferences),
                        cards: {
                          ...(current ?? preferences).cards,
                          [key]: checked,
                        },
                      }))
                    }
                  />
                }
              />
            ))}
          </Stack>
          <Button
            disabled={!ready || busy}
            onClick={() => setDraft(normalizeLiveViewPreferences())}
            sx={{ mt: 1 }}
          >
            {t("views.live.resetDisplaySettings")}
          </Button>
        </DialogContent>
        <DialogActions sx={{ flexWrap: "wrap" }}>
          <Button disabled={busy} onClick={close}>
            {t("common.cancel")}
          </Button>
          <Button
            variant="contained"
            disabled={!ready || busy}
            onClick={() =>
              mutation.mutate(
                { preferences: selection, owner: userName },
                { onSuccess: () => setOpen(false) }
              )
            }
          >
            {t(busy ? "views.live.savingSettings" : "common.save")}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
