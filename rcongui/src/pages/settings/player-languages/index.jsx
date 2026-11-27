import { useEffect, useMemo, useState } from "react";
import { Alert, Box, Button, Card, CardContent, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, MenuItem, Stack, Switch, Tab, Tabs, TextField, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/hooks/useAuth";
import { useBlocker } from "react-router-dom";
import PageHeader from "@/components/shared/PageHeader";
import PlayerLanguageProfile from "@/features/player-language/Profile";
import { allowed, read, write } from "@/features/player-language/api";

export default function PlayerLanguages() {
  const { t } = useTranslation();
  const tr = (key, values) => t("playerLanguages." + key, values);
  const { permissions } = useAuth();
  const canEdit = allowed(permissions, "can_edit_message_templates");
  const canCreate = allowed(permissions, "can_add_message_templates");
  const canProfile = allowed(permissions, "can_view_player_profile");
  const [data, setData] = useState(null), [key, setKey] = useState("");
  const [draft, setDraft] = useState({}), [initial, setInitial] = useState({});
  const [locale, setLocale] = useState("de"), [moreLocale, setMoreLocale] = useState("");
  const [group, setGroup] = useState("all"), [pending, setPending] = useState(null);
  const [error, setError] = useState(""), [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false), [playerInput, setPlayerInput] = useState(""), [playerId, setPlayerId] = useState("");
  const [preview, setPreview] = useState(null);
  const [newTemplate, setNewTemplate] = useState({ title: "", content: "", category: "REASON" });
  const template = data?.templates.find(item => item.key === key);
  const dirty = JSON.stringify(draft) !== JSON.stringify(initial);
  const blocker = useBlocker(dirty);
  const options = data?.templates.filter(item => group === "all" || item.group === group) || [];
  const languages = useMemo(() => [...new Set(["de", "en", "fr", ...Object.keys(draft)])], [draft]);
  const select = item => {
    const next = item.needs_review ? item.saved_translations : item.translations;
    setKey(item.key); setDraft({ ...next }); setInitial({ ...next }); setPreview(null); setNotice("");
  };
  const load = async (selectedKey = key) => {
    const value = await read("get_player_message_catalog");
    setData(value);
    const selected = value.templates.find(item => item.key === selectedKey) || value.templates[0];
    if (selected) select(selected);
  };
  useEffect(() => { let active = true; read("get_player_message_catalog").then(value => {
    if (active) { setData(value); if (value.templates[0]) select(value.templates[0]); }
  }).catch(e => { if (active) setError(e.message); }); return () => { active = false; }; }, []);
  useEffect(() => {
    const warn = e => { if (dirty) { e.preventDefault(); e.returnValue = ""; } };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  const run = async operation => { setBusy(true); setError(""); setNotice(""); try { await operation(); } catch (e) { setError(e.message); } finally { setBusy(false); } };
  const changeTemplate = next => {
    const item = data.templates.find(item => item.key === next);
    if (dirty) setPending({ item }); else select(item);
  };
  const save = () => run(async () => {
    const translations = Object.fromEntries(Object.entries(draft).filter(([, text]) => text.trim()));
    await write("set_player_message_translations", { key, source: template.source, translations, expected_revision: template.revision });
    await load(); setNotice(tr("saved"));
  });
  const checkPreview = () => run(async () => {
    const translations = Object.fromEntries(Object.entries(draft).filter(([, text]) => text.trim()));
    setPreview(await write("preview_player_message", { player_id: playerInput.trim(), text: "", key, translations }));
  });
  const create = () => run(async () => {
    const id = await write("add_message_template", newTemplate);
    setNewTemplate({ title: "", content: "", category: "REASON" }); setGroup("moderation");
    await load("manual:" + id);
  });
  const missing = ["de", "en", "fr"].filter(language => !draft[language]?.trim());
  return <Stack spacing={2} sx={{ minWidth: 0 }}>
    <PageHeader title={tr("title")} subtitle={tr("subtitle")} />
    {error && <Alert severity="error">{error}</Alert>}
    {notice && <Alert severity="success">{notice}</Alert>}
    <Card><CardContent><Stack spacing={1.5}>
      <FormControlLabel label={tr("enabled")} control={<Switch checked={!!data?.enabled} disabled={!canEdit || busy || !data} onChange={(_, enabled) => run(async () => {
        await write("set_player_language_settings", { enabled }); setData(old => ({ ...old, enabled }));
      })} />} />
      {data && !data.enabled && <Alert severity="info">{tr("disabledHint")}</Alert>}
      <Typography variant="body2">{tr("help")}</Typography>
    </Stack></CardContent></Card>
    <Card><CardContent><Stack spacing={2}>
      <Typography component="h2" variant="h6">{tr("templates")}</Typography>
      <TextField select label={tr("group")} value={group} disabled={!data || busy} onChange={e => {
        const nextGroup = e.target.value;
        const item = data.templates.find(item => nextGroup === "all" || item.group === nextGroup);
        if (dirty && item && item.key !== key) setPending({ item, group: nextGroup });
        else { setGroup(nextGroup); if (item) select(item); }
      }}>
        {["all", "moderation", "automod", "autobalancer"].map(value => <MenuItem key={value} value={value}>{tr(value)}</MenuItem>)}
      </TextField>
      <TextField select label={tr("template")} value={options.some(item => item.key === key) ? key : ""} disabled={!data || busy} onChange={e => changeTemplate(e.target.value)}>
        {options.map(item => <MenuItem key={item.key} value={item.key}>{item.title || item.key}</MenuItem>)}
      </TextField>
      {template && <>
        {template.needs_review && <Alert severity="warning">{tr("review")}</Alert>}
        <TextField multiline minRows={2} label={tr("original")} value={template.source} slotProps={{ input: { readOnly: true } }} />
        <Typography variant="body2">{tr("preserve")}</Typography>
        {!!template.placeholders.length && <Typography variant="body2">{tr("placeholders", { fields: template.placeholders.map(field => "{" + field + "}").join(", ") })}</Typography>}
        <Alert severity={missing.length ? "info" : "success"}>{missing.length ? tr("missing", { languages: missing.join(", ") }) : tr("complete")}</Alert>
        <Tabs value={locale} onChange={(_, value) => setLocale(value)} variant="scrollable" scrollButtons="auto" aria-label={tr("translations")}>
          {languages.map(language => <Tab key={language} value={language} label={({ de: "Deutsch", en: "English", fr: "Français" })[language] || language} />)}
        </Tabs>
        <TextField multiline minRows={5} label={tr("translation") + " · " + locale} value={draft[locale] || ""} disabled={!canEdit || busy} onChange={e => { setDraft(old => ({ ...old, [locale]: e.target.value })); setNotice(""); setPreview(null); }} />
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
          <TextField label={tr("moreLanguage")} value={moreLocale} onChange={e => setMoreLocale(e.target.value)} size="small" />
          <Button disabled={!canEdit || !/^[a-z]{2,3}(?:-[a-z]{2,4})?$/.test(moreLocale)} onClick={() => { setDraft(old => ({ ...old, [moreLocale]: old[moreLocale] || "" })); setLocale(moreLocale); setMoreLocale(""); }}>{tr("add")}</Button>
        </Stack>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
          <Button variant="contained" disabled={!canEdit || busy || !dirty} onClick={save}>{tr("save")}</Button>
          <Button disabled={!dirty || busy} onClick={() => { setDraft({ ...initial }); setNotice(""); }}>{tr("discard")}</Button>
          <Button disabled={busy || dirty} onClick={() => run(() => load())}>{tr("reload")}</Button>
        </Stack>
        <TextField label={tr("playerId")} value={playerInput} onChange={e => { setPlayerInput(e.target.value); setPreview(null); }} />
        <Typography variant="body2">{tr("previewHint")}</Typography>
        <Button variant="outlined" disabled={!playerInput.trim() || busy} onClick={checkPreview}>{tr("preview")}</Button>
        {preview && <Alert severity="info"><Stack spacing={1} data-testid="localized-preview"><Typography>{tr("resolved", { language: preview.delivered_language })}</Typography><Typography sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{preview.text}</Typography></Stack></Alert>}
      </>}
    </Stack></CardContent></Card>
    {canProfile && <Card><CardContent><Stack spacing={2}>
      <Typography component="h2" variant="h6">{tr("editProfile")}</Typography>
      <TextField label={tr("playerId")} value={playerInput} onChange={e => setPlayerInput(e.target.value)} />
      <Button disabled={!playerInput.trim()} onClick={() => setPlayerId(playerInput.trim())}>{tr("loadPlayer")}</Button>
      {playerId && <PlayerLanguageProfile key={playerId} playerId={playerId} />}
    </Stack></CardContent></Card>}
    {canCreate && <Card><CardContent><Stack spacing={2}>
      <Typography component="h2" variant="h6">{tr("createTitle")}</Typography>
      <TextField label={tr("templateTitle")} value={newTemplate.title} onChange={e => setNewTemplate(old => ({ ...old, title: e.target.value }))} />
      <TextField label={tr("original")} multiline minRows={3} value={newTemplate.content} onChange={e => setNewTemplate(old => ({ ...old, content: e.target.value }))} />
      <TextField select label={tr("category")} value={newTemplate.category} onChange={e => setNewTemplate(old => ({ ...old, category: e.target.value }))}>
        <MenuItem value="REASON">{tr("reason")}</MenuItem><MenuItem value="MESSAGE">{tr("message")}</MenuItem>
      </TextField>
      <Button disabled={busy || dirty || !newTemplate.title.trim() || !newTemplate.content.trim()} onClick={create}>{tr("create")}</Button>
    </Stack></CardContent></Card>}
    <Dialog open={!!pending || blocker.state === "blocked"} onClose={() => { setPending(null); blocker.reset?.(); }}><DialogTitle>{tr("pending")}</DialogTitle><DialogContent>{tr("confirmDiscard")}</DialogContent><DialogActions><Button onClick={() => { setPending(null); blocker.reset?.(); }}>{tr("cancel")}</Button><Button onClick={() => {
      if (pending) { select(pending.item); if (pending.group) setGroup(pending.group); setPending(null); }
      else blocker.proceed?.();
    }}>{tr("discard")}</Button></DialogActions></Dialog>
  </Stack>;
}
