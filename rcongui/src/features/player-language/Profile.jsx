import { useEffect, useState } from "react";
import { Alert, Accordion, AccordionSummary, AccordionDetails, Button, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/hooks/useAuth";
import { allowed, read, write } from "./api";

export default function PlayerLanguageProfile({ playerId }) {
  const { t } = useTranslation();
  const tr = (key, values) => t("playerLanguages." + key, values);
  const { permissions } = useAuth();
  const canEdit = allowed(permissions, "can_edit_player_account");
  const [profile, setProfile] = useState(null);
  const [language, setLanguage] = useState("de+en");
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let active = true;
    setProfile(null); setError(""); setSaved(false);
    if (playerId) read("get_player_language", { player_id: playerId }).then(data => {
      if (active) { setProfile(data); setLanguage(data.language); }
    }).catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, [playerId]);
  const save = async () => {
    setBusy(true); setError(""); setSaved(false);
    try {
      const data = await write("set_player_language", { player_id: playerId, language });
      setProfile(old => ({ ...old, ...data })); setSaved(true);
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };
  return <Stack spacing={1.5} data-testid="player-language-profile">
    <Typography component="h3" variant="subtitle1">{tr("playerProfile")}</Typography>
    {error && <Alert severity="error">{error}</Alert>}
    {saved && <Alert severity="success">{tr("saved")}</Alert>}
    {profile && <>
      <Typography variant="body2">{tr(profile.source)}</Typography>
      <TextField select label={tr("language")} value={language} disabled={!canEdit || busy} onChange={e => { setLanguage(e.target.value); setSaved(false); }}>
        {[...new Set(["de+en", "de", "en", "fr", profile.language])].map(code => <MenuItem key={code} value={code}>{({ "de+en": tr("bilingual"), de: "Deutsch", en: "English", fr: "Français" })[code] || code}</MenuItem>)}
      </TextField>
      {canEdit && <Button variant="outlined" onClick={save} disabled={busy || language === profile.language}>{tr("choose")}</Button>}
      {!!profile.recent_messages?.length && <Accordion disableGutters>
        <AccordionSummary>{tr("audit")}</AccordionSummary>
        <AccordionDetails><Stack spacing={2}>{profile.recent_messages.map((message, index) => <Stack key={index} spacing={0.5}>
          <Typography variant="caption">{message.action} · {message.language} · {tr(message.outcome)}</Typography>
          <Typography variant="caption">{tr("original")}</Typography><Typography sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{message.original}</Typography>
          <Typography variant="caption">{tr("delivered")}</Typography><Typography sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{message.delivered}</Typography>
        </Stack>)}</Stack></AccordionDetails>
      </Accordion>}
    </>}
  </Stack>;
}
