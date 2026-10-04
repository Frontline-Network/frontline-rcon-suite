/* Use the same account preference as CRCON. Anonymous login pages can use the
   browser's appearance; it never grants access or changes account settings. */
(() => {
  const query = new URLSearchParams(location.search);
  if (query.get("embedded") === "1" && window.parent !== window) {
    document.documentElement.dataset.crconEmbedded = "true";
  }
  try {
    const appearance = JSON.parse(document.getElementById("crcon-admin-appearance").textContent) || {};
    const frontlinePresets = {
      "frontline-gold": ["#c59a4a", "#050706", "#0a0d0a", "#f6f4ef"],
      "tactical-blue": ["#5c9ed6", "#05080b", "#0a1015", "#f2f6f9"],
      "signal-green": ["#56b978", "#050806", "#09110c", "#f2f7f3"],
      "command-red": ["#d66d61", "#090606", "#120b0a", "#faf3f2"],
      neutral: ["#a9aca8", "#070808", "#0d0f0f", "#f4f5f4"],
    };
    const paletteProperties = {
      background: "--body-bg", panel: "--wd-panel", text: "--body-fg",
      loud: "--body-loud-color", muted: "--body-quiet-color", accent: "--primary",
      contrast: "--primary-fg", link: "--link-fg", border: "--hairline-color",
      hover: "--wd-hover", selected: "--wd-tint", error: "--error-fg",
    };
    const apply = (value) => {
      const root = document.documentElement;
      const wardogs = value.preset === "wardogs";
      root.dataset.crconTheme = wardogs ? "wardogs" : "frontline";
      root.dataset.crconMode = value.mode === "system"
        ? (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark")
        : value.mode === "light" ? "light" : "dark";
      for (const property of Object.values(paletteProperties)) root.style.removeProperty(property);
      if (!wardogs) {
        const [accent, background, panel, light] = frontlinePresets[value.preset] || frontlinePresets["frontline-gold"];
        root.style.setProperty("--fl-accent", value.preset === "custom" && /^#[0-9a-f]{6}$/i.test(value.customAccent) ? value.customAccent : accent);
        root.style.setProperty("--fl-background", background);
        root.style.setProperty("--fl-panel", panel);
        root.style.setProperty("--fl-background-light", light);
        // Same-origin React supplies resolved colors, including custom accents
        // and accessibility preferences. Accept only known color properties.
        for (const [name, property] of Object.entries(paletteProperties)) {
          const color = value.colors?.[name];
          if (typeof color === "string" && color.length < 80 && /^(#[0-9a-f]{3,8}|rgba?\([\d.,%\s]+\))$/i.test(color) && CSS.supports("color", color)) root.style.setProperty(property, color);
        }
      }
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
    matchMedia("(prefers-color-scheme: light)").addEventListener("change", () => {
      if (selected.mode === "system" && window.parent === window) apply(selected);
    });
    if (appearance.authenticated && window.parent === window && !query.has("_popup") && !query.has("standalone")) {
      query.delete("embedded");
      const search = query.toString();
      location.replace(`/administration/${location.pathname.replace(/^\/admin\/?/, "")}${search ? `?${search}` : ""}`);
    }
  } catch { /* A missing preference must never prevent sign-in. */ }
})();
