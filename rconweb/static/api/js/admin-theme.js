/* Use the same account preference as CRCON. Anonymous login pages can use the
   browser's appearance; it never grants access or changes account settings. */
(() => {
  const query = new URLSearchParams(location.search);
  if (query.get("embedded") === "1" && window.parent !== window) {
    document.documentElement.dataset.crconEmbedded = "true";
  }
  try {
    const appearance = JSON.parse(document.getElementById("crcon-admin-appearance").textContent) || {};
    const apply = (value) => {
      const root = document.documentElement;
      root.dataset.crconTheme = value.preset === "wardogs" ? "wardogs" : "";
      root.dataset.crconMode = ["light", "dark", "system"].includes(value.mode) ? value.mode : "dark";
      const styles = appearance.wardogsStyles || {};
      const style = Object.prototype.hasOwnProperty.call(styles, value.wardogsStyle) ? value.wardogsStyle : "rose";
      root.dataset.wardogsStyle = style;
      if (styles[style]) {
        root.style.setProperty("--wd-accent-dark", styles[style].accent);
        root.style.setProperty("--wd-accent-light", styles[style].lightAccent);
      }
    };
    // Embedded previews and the standalone admin use the same allowlisted colors.
    window.CRCONAdminAppearance = Object.freeze({ apply });
    let selected = appearance;
    if (!appearance.authenticated) {
      try {
        selected = JSON.parse(localStorage.getItem("frontline-crcon.app"))?.state?.appearance || appearance;
      } catch { /* Storage can be disabled; Django's default stays available. */ }
    }
    apply(selected);
    if (selected.preset !== "wardogs") return;
    if (appearance.authenticated && window.parent === window && !query.has("_popup") && !query.has("standalone")) {
      query.delete("embedded");
      const search = query.toString();
      location.replace(`/administration/${location.pathname.replace(/^\/admin\/?/, "")}${search ? `?${search}` : ""}`);
    }
  } catch { /* A missing preference must never prevent sign-in. */ }
})();
