import { useEffect, useMemo, useState } from "react";
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
  Tabs,
  Tab,
  Box,
} from "@mui/material";
import TuneOutlined from "@mui/icons-material/TuneOutlined";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/hooks/useAuth";
import { cmd } from "@/utils/fetchUtils";
import { PlayerTableSettings } from "./player-table-settings";
import {
  DEFAULT_LIVE_CARDS,
  liveViewPreferencesKey,
  normalizeLiveViewPreferences,
  resetLiveStatusCards,
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
  const preferences = useMemo(
    () => normalizeLiveViewPreferences(query.data),
    [query.data]
  );
  return {
    userName,
    query,
    mutation,
    preferences,
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

export function LiveViewSettings({
  settings,
  open,
  onOpen,
  onClose,
  section,
  onSectionChange,
}) {
  const { t } = useTranslation();
  const { userName, preferences, query, mutation } = settings;
  const [draft, setDraft] = useState(null);
  const selection = draft ?? preferences;
  const busy = mutation.isPending;
  const resetMutation = mutation.reset;
  useEffect(() => {
    if (open) {
      setDraft(null);
      resetMutation();
    }
  }, [open, userName, resetMutation]);
  const close = () => {
    if (!busy) onClose();
  };
  const ready = Boolean(userName && query.isSuccess);
  return (
    <>
      <Button
        size="small"
        disabled={busy}
        aria-label={t("views.live.customizeView")}
        startIcon={<TuneOutlined />}
        onClick={() => onOpen("status")}
        sx={{ flexShrink: 0, m: 0.5 }}
      >
        {t("views.live.displaySettings")}
      </Button>
      <Dialog
        open={open}
        onClose={close}
        fullWidth
        maxWidth="sm"
        aria-labelledby="live-view-settings-title"
      >
        <DialogTitle id="live-view-settings-title">
          {t("views.live.customizeView")}
        </DialogTitle>
        <Tabs
          value={section}
          onChange={(_, value) => onSectionChange(value)}
          variant="fullWidth"
          aria-label={t("views.live.displaySections")}
          sx={{ borderBottom: 1, borderColor: "divider" }}
        >
          <Tab
            id="live-display-tab-status"
            aria-controls="live-display-panel-status"
            value="status"
            label={t("views.live.statusCardsTab")}
          />
          <Tab
            id="live-display-tab-players"
            aria-controls="live-display-panel-players"
            value="players"
            label={t("views.live.playerTableTab")}
          />
        </Tabs>
        {mutation.isError ? (
          <Alert severity="error" sx={{ mx: 3, mt: 1 }}>
            {t("views.live.saveSettingsFailed")}
          </Alert>
        ) : null}
        <DialogContent sx={{ pt: 2, minHeight: 0 }}>
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
          <Box
            role="tabpanel"
            id="live-display-panel-players"
            aria-labelledby="live-display-tab-players"
            hidden={section !== "players"}
          >
            <PlayerTableSettings
              value={selection.players_table}
              disabled={!ready || busy}
              onChange={(players_table) =>
                setDraft((current) => ({
                  ...(current ?? preferences),
                  players_table,
                }))
              }
            />
          </Box>
          <Box
            role="tabpanel"
            id="live-display-panel-status"
            aria-labelledby="live-display-tab-status"
            hidden={section !== "status"}
          >
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
              onClick={() => setDraft(resetLiveStatusCards(selection))}
              sx={{ mt: 1 }}
            >
              {t("views.live.resetDisplaySettings")}
            </Button>
          </Box>
        </DialogContent>
        <DialogActions
          sx={{ flexWrap: "wrap", "& .MuiButton-root": { minHeight: 44 } }}
        >
          <Button disabled={busy} onClick={close}>
            {t("common.cancel")}
          </Button>
          <Button
            variant="contained"
            disabled={!ready || busy}
            onClick={() =>
              mutation.mutate(
                { preferences: selection, owner: userName },
                { onSuccess: onClose }
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
