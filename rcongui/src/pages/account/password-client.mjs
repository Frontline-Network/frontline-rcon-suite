// Secrets are sent only in the POST body, never URLs, caches or diagnostics.
export async function passwordRequest(
  { language, mode = "change", uid, values, csrfToken, signal },
  fetcher = fetch
) {
  const path =
    mode === "request"
      ? "/accounts/password_reset/"
      : mode === "reset"
      ? "/accounts/reset/" + encodeURIComponent(uid) + "/set-password/"
      : "/accounts/password_change/";
  const options = {
    method: values ? "POST" : "GET",
    credentials: "same-origin",
    cache: "no-store",
    signal,
    headers: { Accept: "application/json" },
  };
  if (values) {
    if (!csrfToken) throw new Error("Missing CSRF token");
    options.headers["X-CSRFToken"] = csrfToken;
    const names =
      mode === "request"
        ? ["email"]
        : mode === "reset"
        ? ["new_password1", "new_password2"]
        : ["old_password", "new_password1", "new_password2"];
    options.body = new URLSearchParams(
      names.map((name) => [name, values[name] || ""])
    );
  }
  const response = await fetcher(
    path + "?ui_language=" + (language === "de" ? "de" : "en"),
    options
  );
  let data;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  // A proxy/login HTML response is not proof of a successful change.
  return { ok: response.ok, status: response.status, data };
}
