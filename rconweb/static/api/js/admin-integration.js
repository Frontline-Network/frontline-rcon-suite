(() => {
  if (document.documentElement.dataset.crconEmbedded !== "true") return;
  const origin = location.origin;
  const language = new URL(location.href).searchParams.get("ui_language");
  const withEmbedding = (value) => {
    const url = new URL(value, location.href);
    if (url.origin === origin && url.pathname.startsWith("/admin/")) {
      url.searchParams.set("embedded", "1");
      if (language) url.searchParams.set("ui_language", language);
    }
    return url;
  };
  const links = JSON.parse(document.getElementById("crcon-admin-navigation").textContent);
  const announce = () => {
    const clean = new URL(location.href);
    clean.searchParams.delete("embedded");
    clean.searchParams.delete("ui_language");
    window.parent.postMessage({type: "crcon-admin-page", path: clean.pathname + clean.search, links,
      height: Math.ceil(document.getElementById("container").getBoundingClientRect().height) + 4}, origin);
  };
  document.addEventListener("click", (event) => {
    const link = event.target.closest("a[href]");
    if (!link || link.getAttribute("href").startsWith("#")) return;
    const url = withEmbedding(link.href);
    if (url.origin === origin && url.pathname.startsWith("/admin/")) {
      link.href = url.href;
    } else if (url.origin === origin && link.target !== "_blank") {
      event.preventDefault();
      window.parent.postMessage({type: "crcon-admin-exit", path: url.pathname + url.search + url.hash}, origin);
    }
  }, true);
  document.addEventListener("submit", (event) => {
    const form = event.target;
    form.action = withEmbedding(form.action || location.href).href;
    // GET forms replace the query string, so retain the embedding flag there too.
    if (form.method.toLowerCase() === "get" && !form.querySelector('[name="embedded"]')) {
      const hidden = document.createElement("input");
      hidden.type = "hidden"; hidden.name = "embedded"; hidden.value = "1"; form.append(hidden);
    }
    if (form.method.toLowerCase() === "get" && language && !form.querySelector('[name="ui_language"]')) {
      const hidden = document.createElement("input");
      hidden.type = "hidden"; hidden.name = "ui_language"; hidden.value = language; form.append(hidden);
    }
  }, true);
  window.addEventListener("message", (event) => {
    if (event.origin !== origin || event.source !== window.parent) return;
    if (event.data?.type === "crcon-admin-request-page") { announce(); return; }
    if (event.data?.type !== "crcon-admin-appearance") return;
    window.CRCONAdminAppearance?.apply(event.data);
  });
  new ResizeObserver(announce).observe(document.getElementById("container"));
  announce();
})();
