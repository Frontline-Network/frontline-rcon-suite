import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  FormControlLabel,
  MenuItem,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/hooks/useAuth";
import { canUse } from "@/pages/views/live-map/api";
import { fetchWithCsrf } from "@/utils/fetchUtils";
import { copy } from "./copy";

async function request(data) {
  const response = await fetchWithCsrf("/api/report-admin/v1/config", {
    method: data ? "PUT" : "GET",
    headers: { "Content-Type": "application/json" },
    ...(data ? { body: JSON.stringify(data) } : {}),
  });
  const body = await response.json();
  if (!response.ok || body.failed)
    throw new Error(body.error || `HTTP ${response.status}`);
  return body.result;
}

export default function ReportAdmin({ embedded = false }) {
  const { user, permissions } = useAuth();
  const { i18n } = useTranslation();
  const language = (i18n.resolvedLanguage || i18n.language || "en").split("-")[0];
  const c = copy[language] || copy.en;
  const allowed = canUse(permissions, "can_manage_discord_report_bot");
  const key = ["report-admin", window.location.origin, user?.username];
  const client = useQueryClient();
  const query = useQuery({
    queryKey: key,
    queryFn: () => request(),
    enabled: allowed,
    retry: false,
    refetchOnWindowFocus: false,
  });
  const [draft, setDraft] = useState(null);
  useEffect(() => {
    if (query.data) setDraft(query.data.config);
  }, [query.data]);
  const save = useMutation({
    mutationFn: () => request(draft),
    onSuccess: () => client.invalidateQueries({ queryKey: key }),
  });
  if (!allowed) return null;
  const error = query.error || save.error;
  return (
    <Box
      component="section"
      aria-label={c.title}
      sx={{
        mt: embedded ? 0 : 3,
        p: embedded ? 0 : { xs: 2, md: 3 },
        border: embedded ? "none" : "1px solid",
        borderColor: "divider",
        borderRadius: 2,
      }}
    >
      <Typography component="h2" variant="h5" sx={{ mb: 2 }}>
        {c.title}
      </Typography>
      <Stack spacing={2}>
        <Typography color="text.secondary">{c.info}</Typography>
        <Alert severity="warning">{c.warning}</Alert>
        <Typography>{c.teamkills}</Typography>
        <Typography>{c.cheating}</Typography>
        <Typography>{c.names}</Typography>
        <Typography>{c.memberHelp}</Typography>
        {error && <Alert severity="error">{error.message}</Alert>}
        {save.isSuccess && <Alert severity="success">{c.saved}</Alert>}
        {!draft ? (
          <Typography>{c.loading}</Typography>
        ) : (
          <Stack
            component="form"
            spacing={2}
            onSubmit={(e) => {
              e.preventDefault();
              save.mutate();
            }}
          >
            {[
              ["enabled", c.enabled],
              ["communication", c.communication],
              ["communication_squad_members", c.members],
              ["teamkills", c.tk],
              ["cheating", c.cheatToggle],
              ["allow_self_reports", c.selfReports],
            ].map(([name, label]) => (
              <FormControlLabel
                key={name}
                label={label}
                control={
                  <Switch
                    checked={Boolean(draft[name])}
                    disabled={
                      save.isPending ||
                      (name === "enabled" &&
                        !query.data.can_enable &&
                        !draft.enabled)
                    }
                    onChange={(e) =>
                      setDraft({ ...draft, [name]: e.target.checked })
                    }
                  />
                }
              />
            ))}
            {draft.allow_self_reports && (
              <Alert severity="warning">{c.selfReportsWarning}</Alert>
            )}
            <TextField
              select
              label={c.reasonMode}
              value={draft.reason_mode ?? "rules"}
              disabled={save.isPending}
              onChange={(e) =>
                setDraft({ ...draft, reason_mode: e.target.value })
              }
              helperText={
                draft.reason_mode === "ai" ? c.aiReasonHelp : c.rulesReasonHelp
              }
            >
              <MenuItem value="ai">{c.aiReason}</MenuItem>
              <MenuItem value="rules">{c.rulesReason}</MenuItem>
            </TextField>
            <TextField
              select
              label={c.receiptLanguage}
              value={draft.receipt_language ?? "de+en"}
              disabled={save.isPending}
              onChange={(e) => setDraft({ ...draft, receipt_language: e.target.value })}
              helperText={c.receiptLanguageHelp}
            >
              <MenuItem value="de+en">Deutsch + English</MenuItem>
              <MenuItem value="de">Deutsch</MenuItem>
              <MenuItem value="en">English</MenuItem>
              <MenuItem value="fr">Français</MenuItem>
            </TextField>
            <TextField
              select
              label={c.mode}
              value={draft.mode}
              onChange={(e) => setDraft({ ...draft, mode: e.target.value })}
            >
              <MenuItem value="dry_run">{c.dry}</MenuItem>
              <MenuItem value="active">{c.active}</MenuItem>
            </TextField>
            {[
              ["communication_template_id", c.commTemplate],
              ["teamkills_template_id", c.tkTemplate],
            ].map(([name, label]) => (
              <TextField
                key={name}
                select
                label={label}
                value={draft[name] ?? ""}
                onChange={(e) =>
                  setDraft({
                    ...draft,
                    [name]:
                      e.target.value === "" ? null : Number(e.target.value),
                  })
                }
              >
                <MenuItem value="">{c.fallback}</MenuItem>
                {(query.data.templates || []).map((item) => (
                  <MenuItem value={item.id} key={item.id}>
                    {item.title}
                  </MenuItem>
                ))}
              </TextField>
            ))}
            <Typography variant="body2" color="text.secondary">
              {c.placeholders}
            </Typography>
            <Button
              type="submit"
              variant="contained"
              disabled={
                save.isPending || (draft.enabled && !query.data.can_enable)
              }
            >
              {c.save}
            </Button>
          </Stack>
        )}
      </Stack>
    </Box>
  );
}
