import { useEffect, useMemo, useState } from "react";
import { Accordion, AccordionDetails, AccordionSummary, Alert, Autocomplete, Box, Button, Card, CardContent, Chip, Dialog, DialogActions, DialogContent, DialogTitle, Divider, FormControlLabel, LinearProgress, MenuItem, Stack, Switch, Tab, Tabs, TextField, Typography, createFilterOptions } from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import AddIcon from "@mui/icons-material/Add";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/hooks/useAuth";
import { useBlocker } from "react-router-dom";
import PageHeader from "@/components/shared/PageHeader";
import PlayerLanguageProfile from "@/features/player-language/Profile";
import { allowed, read, write } from "@/features/player-language/api";
import { templateLabel, templateSection, translationStatus } from "@/features/player-language/templateLabels";

const languageNames = { de: "Deutsch", en: "English", fr: "Français" };

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
  const [group, setGroup] = useState("all"), [status, setStatus] = useState("all");
  const [tab, setTab] = useState("templates"), [createOpen, setCreateOpen] = useState(false);
  const [pending, setPending] = useState(null);
  const [error, setError] = useState(""), [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false), [previewInput, setPreviewInput] = useState("");
  const [profileInput, setProfileInput] = useState(""), [playerId, setPlayerId] = useState("");
  const [preview, setPreview] = useState(null);
  const [newTemplate, setNewTemplate] = useState({ title: "", content: "", category: "REASON" });
  const template = data?.templates.find(item => item.key === key);
  const dirty = JSON.stringify(draft) !== JSON.stringify(initial);
  const blocker = useBlocker(dirty);
  const languages = useMemo(() => [...new Set(["de", "en", "fr", ...Object.keys(draft)])], [draft]);
  const matches = (item, nextGroup = group, nextStatus = status) =>
    (nextGroup === "all" || item.group === nextGroup) && (nextStatus === "all" || translationStatus(item) === nextStatus);
  const options = (data?.templates || []).filter(item => matches(item))
    .sort((a, b) => templateSection(a, t).localeCompare(templateSection(b, t)) || templateLabel(a, t).localeCompare(templateLabel(b, t)));
  const select = item => {
    if (!item) { setKey(""); setDraft({}); setInitial({}); setPreview(null); return; }
    const next = item.needs_review ? item.saved_translations : item.translations;
    setKey(item.key); setDraft({ ...next }); setInitial({ ...next }); setPreview(null); setNotice("");
  };
  const load = async (selectedKey = key) => {
    const value = await read("get_player_message_catalog");
    setData(value);
    const selected = value.templates.find(item => item.key === selectedKey) || value.templates[0];
    if (selected && !matches(selected)) setStatus("all");
    if (selected && group !== "all" && selected.group !== group) setGroup(selected.group);
    select(selected);
  };
  useEffect(() => {
    let active = true;
    read("get_player_message_catalog").then(value => {
      if (active) { setData(value); select(value.templates[0]); }
    }).catch(e => { if (active) setError(e.message); });
    return () => { active = false; };
  }, []);
  useEffect(() => {
    const warn = e => { if (dirty) { e.preventDefault(); e.returnValue = ""; } };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  const run = async operation => {
    setBusy(true); setError(""); setNotice("");
    try { await operation(); } catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  const requestSelection = change => {
    if (dirty && change.item?.key !== key) setPending(change);
    else {
      if (change.group !== undefined) setGroup(change.group);
      if (change.status !== undefined) setStatus(change.status);
      select(change.item);
    }
  };
  const filter = (nextGroup, nextStatus) => {
    const item = data.templates.find(item => item.key === key && matches(item, nextGroup, nextStatus)) ||
      data.templates.find(item => matches(item, nextGroup, nextStatus));
    if (item?.key === key) { setGroup(nextGroup); setStatus(nextStatus); }
    else requestSelection({ item, group: nextGroup, status: nextStatus });
  };
  const translations = () => Object.fromEntries(Object.entries(draft).filter(([, text]) => text.trim()));
  const save = () => run(async () => {
    await write("set_player_message_translations", { key, source: template.source, translations: translations(), expected_revision: template.revision });
    await load(); setNotice(tr("saved"));
  });
  const checkPreview = () => run(async () => {
    setPreview(await write("preview_player_message", { player_id: previewInput.trim(), text: "", key, translations: translations() }));
  });
  const create = () => run(async () => {
    const id = await write("add_message_template", newTemplate);
    setNewTemplate({ title: "", content: "", category: "REASON" });
    setGroup("moderation"); setStatus("all"); setCreateOpen(false);
    await load("manual:" + id);
  });
  const missing = template?.source.trim() ? ["de", "en", "fr"].filter(language => !draft[language]?.trim()) : [];

  return <Stack spacing={2.5} sx={{ minWidth: 0, maxWidth: 1600 }}>
    <PageHeader title={tr("title")} subtitle={tr("subtitle")} />
    {error && !createOpen && <Alert severity="error" action={!data ? <Button onClick={() => run(() => load())} disabled={busy}>{tr("reload")}</Button> : undefined}>{error}</Alert>}
    {notice && <Alert severity="success">{notice}</Alert>}
    {!data && !error && <LinearProgress aria-label={tr("reload")} />}
    <Card><CardContent>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" spacing={2} alignItems={{ sm: "center" }}>
        <Stack spacing={0.75}>
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
            <Typography component="h2" variant="subtitle1" fontWeight={600}>{tr("routingTitle")}</Typography>
            {data && <Chip size="small" color={data.enabled ? "success" : "default"} label={tr(data.enabled ? "active" : "inactive")} variant="outlined" />}
          </Stack>
          <Typography variant="body2" color="text.secondary">{tr("routingHint")}</Typography>
        </Stack>
        <FormControlLabel sx={{ flexShrink: 0 }} label={tr("active")} control={<Switch checked={!!data?.enabled} disabled={!canEdit || busy || !data}
          inputProps={{ "aria-label": tr("enabled") }} onChange={(_, enabled) => run(async () => {
            await write("set_player_language_settings", { enabled }); setData(old => ({ ...old, enabled }));
          })} />} />
      </Stack>
      {data && !data.enabled && <Alert severity="info" sx={{ mt: 2 }}>{tr("disabledHint")}</Alert>}
    </CardContent></Card>
    <Tabs value={tab} onChange={(_, next) => setTab(next)} aria-label={tr("workspace")} variant="scrollable">
      <Tab value="templates" label={tr("manageTemplates")} id="language-templates-tab" aria-controls="language-templates-panel" />
      {canProfile && <Tab value="players" label={tr("managePlayers")} id="language-players-tab" aria-controls="language-players-panel" />}
    </Tabs>
    <Stack role="tabpanel" id="language-templates-panel" aria-labelledby="language-templates-tab" hidden={tab !== "templates"} spacing={2.5} sx={{ display: tab === "templates" ? undefined : "none" }}>
      <Card><CardContent><Stack spacing={2}>
        <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" spacing={1}>
          <Box><Typography component="h2" variant="h6">{tr("templates")}</Typography>
            <Typography variant="body2" color="text.secondary">{tr("templateHint")}</Typography></Box>
          {canCreate && <Button startIcon={<AddIcon />} variant="outlined" disabled={busy || dirty} onClick={() => { setError(""); setCreateOpen(true); }} sx={{ alignSelf: { xs: "flex-start", sm: "center" }, flexShrink: 0 }}>{tr("createTitle")}</Button>}
        </Stack>
        <Stack direction={{ xs: "column", md: "row" }} spacing={1.5}>
          <TextField select size="small" label={tr("group")} value={group} disabled={!data || busy} onChange={e => filter(e.target.value, status)} sx={{ minWidth: { md: 190 } }}>
            {["all", "moderation", "automod", "autobalancer"].map(value => <MenuItem key={value} value={value}>{tr(value)}</MenuItem>)}
          </TextField>
          <TextField select size="small" label={tr("status")} value={status} disabled={!data || busy} onChange={e => filter(group, e.target.value)} sx={{ minWidth: { md: 210 } }}>
            {["all", "incomplete", "needsReview", "ready"].map(value => <MenuItem key={value} value={value}>{tr(value === "all" ? "allStatuses" : value)}</MenuItem>)}
          </TextField>
          <Autocomplete sx={{ flex: 1, minWidth: 0 }} size="small" disabled={!data || busy} disableClearable
            options={options} value={template || null} getOptionLabel={item => templateLabel(item, t)}
            isOptionEqualToValue={(a, b) => a.key === b.key} groupBy={item => templateSection(item, t)}
            filterOptions={createFilterOptions({ stringify: item => templateLabel(item, t) + " " + item.source })}
            noOptionsText={tr("noTemplates")} openText={tr("openTemplates")} closeText={tr("closeTemplates")}
            onChange={(_, item) => { if (item) requestSelection({ item }); }}
            renderOption={(props, item) => {
              const { key: optionKey, ...optionProps } = props;
              return <Box component="li" key={optionKey + item.key} {...optionProps} sx={{ display: "flex", gap: 1.5, justifyContent: "space-between !important", minWidth: 0 }}>
                <Box sx={{ minWidth: 0 }}><Typography variant="body2" sx={{ overflowWrap: "anywhere" }}>{templateLabel(item, t)}</Typography>
                  {!!item.title && <Typography variant="caption" color="text.secondary" noWrap sx={{ display: "block", maxWidth: { xs: 180, sm: 360 } }}>{item.source}</Typography>}
                </Box>
                <Chip size="small" label={tr(translationStatus(item))} color={translationStatus(item) === "ready" ? "success" : "default"} variant="outlined" sx={{ flexShrink: 0 }} />
              </Box>;
            }} renderInput={params => <TextField {...params} label={tr("searchTemplates")} placeholder={tr("searchHint")} />}
          />
        </Stack>
        <Typography variant="caption" color="text.secondary">{tr("templateCount", { count: options.length })}</Typography>
        {data && !options.length && <Alert severity="info">{tr("noTemplates")}</Alert>}
      </Stack></CardContent></Card>
      {template && <Card><CardContent><Stack spacing={2.5}>
        <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" spacing={1}>
          <Box><Typography variant="overline" color="text.secondary">{templateSection(template, t)}</Typography>
            <Typography component="h2" variant="h6">{templateLabel(template, t)}</Typography></Box>
          <Stack direction="row" alignItems="center" spacing={0.75} flexWrap="wrap" useFlexGap>
            {["de", "en", "fr"].map(code => <Chip key={code} size="small" label={languageNames[code]} color={draft[code]?.trim() ? "success" : "default"} variant="outlined" />)}
          </Stack>
        </Stack>
        {template.needs_review && <Alert severity="warning">{tr("review")}</Alert>}
        {!!missing.length && <Alert severity="info">{tr("missing", { languages: missing.map(code => languageNames[code]).join(", ") })}</Alert>}
        <Tabs value={locale} onChange={(_, value) => setLocale(value)} variant="scrollable" scrollButtons="auto" aria-label={tr("translations")}>
          {languages.map(language => <Tab key={language} value={language} label={languageNames[language] || language} />)}
        </Tabs>
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "minmax(0, 1fr)", lg: "repeat(2, minmax(0, 1fr))" }, gap: 3 }}>
          <Stack spacing={1.5} sx={{ minWidth: 0 }}>
            <Typography component="h3" variant="subtitle2">{tr("original")}</Typography>
            <TextField multiline rows={6} label={tr("original")} value={template.source} slotProps={{ input: { readOnly: true } }} fullWidth />
            <Typography variant="caption" color="text.secondary">{tr("sourceHint")}</Typography>
          </Stack>
          <Stack spacing={1.5} sx={{ minWidth: 0 }}>
            <Typography component="h3" variant="subtitle2">{tr("translation")}</Typography>
            <TextField multiline rows={6} label={tr("translation") + " · " + locale} value={draft[locale] || ""} disabled={!canEdit || busy} onChange={e => {
              setDraft(old => ({ ...old, [locale]: e.target.value })); setNotice(""); setPreview(null);
            }} fullWidth />
            <Typography variant="caption" color="text.secondary">{tr("editHint")}</Typography>
          </Stack>
        </Box>
        {!!template.placeholders.length && <Stack direction="row" alignItems="center" flexWrap="wrap" gap={0.75}>
          <Typography variant="caption" color="text.secondary">{tr("placeholders", { fields: "" })}</Typography>
          {template.placeholders.map(field => <Chip key={field} size="small" label={"{" + field + "}"} sx={{ fontFamily: "monospace" }} />)}
        </Stack>}
        {canEdit && <Accordion disableGutters elevation={0} sx={{ bgcolor: "transparent", alignSelf: "flex-start", width: "100%", maxWidth: 480, "&:before": { display: "none" } }}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>{tr("addLanguage")}</AccordionSummary>
              <AccordionDetails><Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
                <TextField size="small" label={tr("languageCode")} placeholder="pl" value={moreLocale} disabled={busy} onChange={e => setMoreLocale(e.target.value.trim().toLowerCase())} />
                <Button disabled={busy || !/^[a-z]{2,3}(?:-[a-z]{2,4})?$/.test(moreLocale)} onClick={() => {
                  setDraft(old => ({ ...old, [moreLocale]: old[moreLocale] || "" })); setLocale(moreLocale); setMoreLocale(""); setPreview(null);
                }}>{tr("add")}</Button>
              </Stack></AccordionDetails>
            </Accordion>}
        <Divider />
        <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" alignItems={{ sm: "center" }} spacing={1.5}>
          <Typography role="status" variant="body2" color={dirty ? "warning.main" : "text.secondary"}>{tr(dirty ? "dirtyState" : "savedState")}</Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Button disabled={busy || dirty} onClick={() => run(() => load())}>{tr("reload")}</Button>
            <Button disabled={!dirty || busy} onClick={() => { setDraft({ ...initial }); setNotice(""); setPreview(null); }}>{tr("discard")}</Button>
            <Button variant="contained" disabled={!canEdit || busy || !dirty} onClick={save}>{tr("save")}</Button>
          </Stack>
        </Stack>
      </Stack></CardContent></Card>}
      {template && <Card><CardContent><Stack spacing={2}>
        <Box><Typography component="h2" variant="subtitle1" fontWeight={600}>{tr("previewTitle")}</Typography>
          <Typography variant="body2" color="text.secondary">{tr("previewHelp")}</Typography></Box>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ sm: "flex-start" }}>
          <TextField size="small" sx={{ flex: 1 }} label={tr("previewPlayerId")} value={previewInput} onChange={e => { setPreviewInput(e.target.value); setPreview(null); }} />
          <Button variant="outlined" disabled={!previewInput.trim() || busy} onClick={checkPreview}>{tr("preview")}</Button>
        </Stack>
        {preview && <Alert severity="info"><Stack spacing={1} data-testid="localized-preview">
          <Typography>{tr("resolved", { language: preview.delivered_language })}</Typography>
          <Typography sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{preview.text}</Typography>
        </Stack></Alert>}
        <Typography variant="caption" color="text.secondary">{tr("preserve")}</Typography>
      </Stack></CardContent></Card>}
    </Stack>
    {canProfile && <Card role="tabpanel" id="language-players-panel" aria-labelledby="language-players-tab" hidden={tab !== "players"} sx={{ display: tab === "players" ? undefined : "none" }}>
      <CardContent><Stack spacing={2}>
        <Typography component="h2" variant="h6">{tr("editProfile")}</Typography>
        <Typography variant="body2" color="text.secondary">{tr("profileHint")}</Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
          <TextField label={tr("profilePlayerId")} value={profileInput} onChange={e => setProfileInput(e.target.value)} size="small" sx={{ flex: 1 }} />
          <Button variant="outlined" disabled={!profileInput.trim()} onClick={() => setPlayerId(profileInput.trim())}>{tr("loadPlayer")}</Button>
        </Stack>
        {playerId && <PlayerLanguageProfile key={playerId} playerId={playerId} />}
        <Divider /><Typography variant="body2" color="text.secondary">{tr("help")}</Typography>
      </Stack></CardContent>
    </Card>}
    <Dialog open={createOpen} onClose={() => { if (!busy) setCreateOpen(false); }} fullWidth maxWidth="sm" aria-labelledby="new-language-template-title">
      <DialogTitle id="new-language-template-title">{tr("createTitle")}</DialogTitle>
      <DialogContent><Stack spacing={2} sx={{ pt: 1 }}>
        {error && <Alert severity="error">{error}</Alert>}
        <Typography variant="body2" color="text.secondary">{tr("createHint")}</Typography>
        <TextField label={tr("templateTitle")} value={newTemplate.title} disabled={busy} onChange={e => setNewTemplate(old => ({ ...old, title: e.target.value }))} />
        <TextField label={tr("original")} multiline minRows={4} disabled={busy} value={newTemplate.content} onChange={e => setNewTemplate(old => ({ ...old, content: e.target.value }))} />
        <TextField select label={tr("category")} value={newTemplate.category} disabled={busy} onChange={e => setNewTemplate(old => ({ ...old, category: e.target.value }))}>
          <MenuItem value="REASON">{tr("reason")}</MenuItem><MenuItem value="MESSAGE">{tr("message")}</MenuItem>
        </TextField>
      </Stack></DialogContent>
      <DialogActions><Button disabled={busy} onClick={() => setCreateOpen(false)}>{tr("cancel")}</Button>
        <Button variant="contained" disabled={busy || dirty || !newTemplate.title.trim() || !newTemplate.content.trim()} onClick={create}>{tr("create")}</Button></DialogActions>
    </Dialog>
    <Dialog open={!!pending || blocker.state === "blocked"} onClose={() => { setPending(null); blocker.reset?.(); }}>
      <DialogTitle>{tr("pending")}</DialogTitle><DialogContent>{tr("confirmDiscard")}</DialogContent>
      <DialogActions><Button onClick={() => { setPending(null); blocker.reset?.(); }}>{tr("cancel")}</Button><Button onClick={() => {
        if (pending) {
          select(pending.item);
          if (pending.group !== undefined) setGroup(pending.group);
          if (pending.status !== undefined) setStatus(pending.status);
          setPending(null);
        } else blocker.proceed?.();
      }}>{tr("discard")}</Button></DialogActions>
    </Dialog>
  </Stack>;
}
