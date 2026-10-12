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
  const api = {normalize, matches, bundleState, changes};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.CRCONPermissionPlanner = api;
})(typeof window !== "undefined" ? window : globalThis);
