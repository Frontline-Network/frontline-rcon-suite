const RECOVERY_HEADER = "X-CRCON-CSRF-Recovery";
const TOKEN_HEADER = "X-CRCON-CSRF-Token";
const ERROR_HEADER = "X-CRCON-CSRF-Error";
const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS", "TRACE"]);

export const isUnsafeMethod = (method) =>
  !SAFE_METHODS.has(String(method || "GET").toUpperCase());

export function csrfFailureKind(response) {
  if (response.status !== 403) return null;
  // Also recognize the previous backend's HTML recovery response during rolling updates.
  return (
    response.headers.get(ERROR_HEADER) ||
    (response.headers.get(RECOVERY_HEADER) === "1" ? "token" : null)
  );
}

export class CsrfTransportError extends Error {
  constructor(code) {
    super(code);
    this.name = "CsrfTransportError";
    this.code = code;
    this.status = 403;
  }
}

/** One in-memory token coordinator per API. Never persist tokens or log them. */
export function createCsrfTransport({
  apiBase,
  pageOrigin,
  fetcher,
  readCookie,
}) {
  const base = new URL(apiBase, pageOrigin);
  const authUrl = new URL("is_logged_in", base);
  let token = null;
  let tokenCookie = null;
  let generation = 0;
  let version = 0;
  let refreshPromise = null;

  const cookieSnapshot = () =>
    base.origin === pageOrigin
      ? readCookie()
          .split(";")
          .map((part) => part.trim())
          .filter((part) => part.startsWith("csrftoken="))
          .join(";")
      : "";

  function reset() {
    generation += 1;
    version += 1;
    token = null;
    tokenCookie = null;
  }

  function currentToken() {
    if (token && tokenCookie !== cookieSnapshot()) {
      // A login in another tab (or a removed cookie) invalidates the cached token.
      token = null;
      version += 1;
    }
    return token;
  }

  function acceptToken(response, expectedGeneration) {
    if (generation !== expectedGeneration || !response.ok) return;
    token = response.headers.get(TOKEN_HEADER);
    tokenCookie = cookieSnapshot();
    // During a rolling update an older API may not expose the token on auth
    // responses yet. Only fall back to a single unambiguous, well-formed cookie;
    // never choose the first of several path/domain cookies.
    if (
      !token &&
      /^csrftoken=([a-zA-Z0-9]{32}|[a-zA-Z0-9]{64})$/.test(tokenCookie)
    ) {
      token = tokenCookie.slice("csrftoken=".length);
    }
    version += 1;
  }

  async function refreshSession() {
    // Bootstrap *before* parallel writes: separate missing-cookie POST failures
    // could otherwise each issue a different Set-Cookie and invalidate each other.
    if (!refreshPromise) {
      const startedGeneration = generation;
      const pending = (async () => {
        const response = await fetcher(authUrl, {
          method: "GET",
          credentials: "include",
          cache: "no-store",
          headers: { Accept: "application/json" },
        });
        acceptToken(response, startedGeneration);
        return { response, generation: startedGeneration };
      })();
      refreshPromise = pending;
      // Do not let an earlier completion clear a newer refresh.
      pending.then(
        () => {
          if (refreshPromise === pending) refreshPromise = null;
        },
        () => {
          if (refreshPromise === pending) refreshPromise = null;
        }
      );
    }
    const refreshed = await refreshPromise;
    if (refreshed.generation !== generation) {
      // A login/logout occurred during the previous check. Never adopt its token.
      return refreshSession();
    }
    return refreshed.response.clone();
  }

  function checkPendingRequest(expectedGeneration, signal) {
    signal?.throwIfAborted();
    if (generation !== expectedGeneration) {
      throw new CsrfTransportError("session_changed");
    }
  }

  async function fetchWithCsrf(input, options = {}) {
    const url = new URL(input, pageOrigin);
    const headers = new Headers(options.headers || {});
    // Never attach a session token to another host/API or a token-only integration.
    if (
      url.origin !== base.origin ||
      !url.pathname.startsWith(base.pathname) ||
      options.credentials === "omit" ||
      (options.credentials === "same-origin" && url.origin !== pageOrigin)
    ) {
      return fetcher(input, options);
    }
    const method = String(options.method || "GET").toUpperCase();
    const unsafe = isUnsafeMethod(method);
    const command = url.pathname.slice(base.pathname.length).replace(/\/$/, "");
    const changesSession = command === "login" || command === "logout";
    if (changesSession) reset();
    const startedGeneration = generation;

    if (method === "GET" && url.pathname === authUrl.pathname) {
      const response = await refreshSession();
      checkPendingRequest(startedGeneration, options.signal);
      return response;
    }

    try {
      if (unsafe && !currentToken()) {
        const bootstrap = await refreshSession();
        if (!bootstrap.ok) throw new CsrfTransportError("refresh_failed");
      }
      checkPendingRequest(startedGeneration, options.signal);
      const send = () => {
        const requestHeaders = new Headers(headers);
        if (unsafe && currentToken()) requestHeaders.set("X-CSRFToken", token);
        return fetcher(input, {
          ...options,
          method,
          credentials: options.credentials || "include",
          headers: requestHeaders,
        });
      };
      const sentVersion = version;
      let response = await send();
      if (
        unsafe &&
        response.status === 403 &&
        response.headers.get(RECOVERY_HEADER) === "1" &&
        csrfFailureKind(response) === "token" &&
        generation === startedGeneration
      ) {
        // Only the backend's explicit pre-execution rejection permits a replay.
        // Ignore tokens on rejection responses: a late response must not overwrite
        // a newer token. Refresh through the same shared GET as application startup.
        if (!currentToken() || version === sentVersion) {
          try {
            const refreshed = await refreshSession();
            if (!refreshed.ok) return response;
          } catch {
            return response;
          }
        }
        checkPendingRequest(startedGeneration, options.signal);
        if (currentToken()) response = await send(); // Exactly one retry; no loop.
      }
      if (generation === startedGeneration) {
        if (changesSession) {
          reset();
          if (command === "login") acceptToken(response, generation);
        } else if (response.status === 401) {
          reset();
        } else if (csrfFailureKind(response)) {
          token = null;
        }
      }
      return response;
    } catch (error) {
      if (changesSession && generation === startedGeneration) reset();
      throw error; // Never retry network failures or uncertain action outcomes.
    }
  }

  return { fetchWithCsrf, reset };
}
