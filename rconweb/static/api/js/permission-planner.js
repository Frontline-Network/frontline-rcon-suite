/* Pure presentation helpers; no grants, network requests or form submission. */
((root) => {
  const normalize = (value) => String(value || "").toLocaleLowerCase()
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/ß/g, "ss");
  const matches = (text, query) => normalize(query).split(/\s+/).filter(Boolean)
    .every(word => normalize(text).includes(word));
  const bundleState = (bundle, own, inherited, available, allAccess = false) => {
    const missing = bundle.permissions.filter(id => !allAccess && !own.has(id) && !inherited.has(id));
    const unavailable = [...(bundle.unavailable || []), ...bundle.permissions.filter(id => !available.has(id))];
    return {missing, unavailable, complete: missing.length === 0 && unavailable.length === 0};
  };
  const changes = (initial, current) => ({
    added: [...current].filter(id => !initial.has(id)),
    removed: [...initial].filter(id => !current.has(id)),
  });
  // Draft only: applying and saving remain separate, explicit user actions.
  const wizardPlan = (workflows, answers, own, available) => {
    const allow = new Map(), deny = new Map(), unavailable = [], invalid = [];
    const remember = (map, id, title) => map.set(id, [...(map.get(id) || []), title]);
    workflows.forEach(workflow => {
      const answer = answers[workflow.id];
      if (!answer || answer.mode === 'keep') return;
      if (!['none', 'read', 'custom'].includes(answer.mode)) { invalid.push(workflow.id); return; }
      const actions = new Set(answer.actions || []);
      const knownActions = new Set(workflow.bundles.slice(1).map(b => b.id));
      if ([...actions].some(id => !knownActions.has(id))) invalid.push(workflow.id);
      const selected = answer.mode === 'none' ? [] : workflow.bundles.filter((b, i) => i === 0 || (answer.mode === 'custom' && actions.has(b.id)));
      const wanted = new Set(selected.flatMap(b => b.permissions));
      selected.forEach(b => unavailable.push(...(b.unavailable || []), ...b.permissions.filter(id => !available.has(id))));
      new Set(workflow.bundles.flatMap(b => b.permissions)).forEach(id => remember(wanted.has(id) ? allow : deny, id, workflow.title));
    });
    const conflicts = [...allow.keys()].filter(id => deny.has(id)).map(id => ({id, allow:allow.get(id), deny:deny.get(id)}));
    const next = new Set(own);
    deny.forEach((_, id) => next.delete(id));
    allow.forEach((_, id) => { if (available.has(id)) next.add(id); });
    const affected = workflows.filter(w => !answers[w.id] || answers[w.id].mode === 'keep').flatMap(w => {
      const changed = new Set(w.bundles.flatMap(b => b.permissions).filter(id => own.has(id) !== next.has(id)));
      return changed.size ? [{id:w.id, title:w.title, permissions:[...changed]}] : [];
    });
    return {next, ...changes(own, next), conflicts, unavailable:[...new Set(unavailable)], invalid, affected};
  };
  const api = {normalize, matches, bundleState, changes, wizardPlan};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.CRCONPermissionPlanner = api;
})(typeof window !== "undefined" ? window : globalThis);
