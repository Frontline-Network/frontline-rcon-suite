export function registerPlayerLanguages(server, ok) {
  let enabled = false;
  const profiles = new Map();
  const templates = [
    { key: "manual:1", title: "Serverregeln", group: "moderation", action: "reason", source: "Bitte beachte die Serverregeln.", defaults: {}, translations: { de: "Bitte beachte die Serverregeln.", en: "Please follow the server rules.", fr: "Veuillez respecter les règles du serveur." }, placeholders: [] },
    { key: "automod.no_leader.warning", group: "automod", action: "warning", source: "Warning {player_name}: no squad leader.", defaults: {}, translations: { de: "Achtung {player_name}: kein Squadleader.", en: "Warning {player_name}: no squad leader.", fr: "Attention {player_name} : aucun chef d’escouade." }, placeholders: ["player_name"] },
    { key: "autobalancer.disabled", group: "autobalancer", action: "message", source: "Der Autobalancer ist ausgeschaltet.", defaults: {}, translations: { de: "Der Autobalancer ist ausgeschaltet.", en: "Autobalancing is disabled.", fr: "L’équilibrage automatique est désactivé." }, placeholders: [] },
  ].map(item => ({ ...item, saved_translations: {}, revision: "1", needs_review: false, source_hash: "demo" }));
  const profile = id => profiles.get(id) || { language: "de+en", explicit: false, source: "fallback", updated: null, recent_messages: [] };
  const body = request => JSON.parse(request.requestBody || "{}");
  server.get("/get_player_message_catalog", () => ok({ enabled, templates: structuredClone(templates) }));
  server.post("/set_player_language_settings", (_, request) => { enabled = body(request).enabled; return ok(true); });
  server.post("/set_player_message_translations", (_, request) => {
    const payload = body(request), template = templates.find(item => item.key === payload.key);
    if (!template || payload.expected_revision !== template.revision) return { failed: true, error: "Template changed; reload before saving translations" };
    const expected = JSON.stringify([...template.placeholders].sort());
    for (const value of Object.values(payload.translations)) {
      const fields = [...new Set([...value.matchAll(/\{([\w]+)\}/g)].map(match => match[1]))].sort();
      if (JSON.stringify(fields) !== expected) return { failed: true, error: "Every translation must preserve all placeholders and formats" };
    }
    template.translations = { ...payload.translations };
    template.saved_translations = { ...payload.translations };
    template.revision = String(Number(template.revision) + 1);
    return ok(true);
  });
  server.get("/get_player_language", (_, request) => ok(structuredClone(profile(request.queryParams.player_id))));
  server.post("/set_player_language", (_, request) => {
    const { player_id: id, language } = body(request);
    const value = { ...profile(id), language, source: "selected", explicit: true, updated: Date.now() / 1000 };
    profiles.set(id, value);
    return ok(value);
  });
  server.post("/preview_player_message", (_, request) => {
    const payload = body(request), p = profile(payload.player_id);
    const template = templates.find(item => payload.key ? item.key === payload.key : item.source === payload.text);
    const variants = payload.translations || template?.translations || {};
    const active = !!payload.key || enabled;
    const text = active && template ? variants[p.language] || [...new Set([variants.de, variants.en].filter(Boolean))].join(" / ") || template.source : payload.text;
    return ok({ ...p, text, original: template?.source || payload.text, template_key: active ? template?.key : null, delivered_language: active && template ? variants[p.language] ? p.language : "de+en" : "legacy" });
  });
}
