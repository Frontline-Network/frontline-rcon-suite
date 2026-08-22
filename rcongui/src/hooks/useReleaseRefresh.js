import { useEffect, useRef } from "react";

import { fetchWithCsrf } from "@/utils/fetchUtils";

const RELEASE_CHECK_INTERVAL_MS = 60_000;
const RELEASE_RELOAD_KEY_PREFIX = "crcon.release-refresh:";

const normalizeVersion = (value) => String(value ?? "").trim();

const isUsableVersion = (value) =>
  Boolean(value) && !["unknown", "development", "undefined"].includes(value);

export function useReleaseRefresh() {
  const reloadAttempted = useRef(false);

  useEffect(() => {
    const runtimeVersion = normalizeVersion(process.env.REACT_APP_VERSION);
    if (!isUsableVersion(runtimeVersion)) return undefined;

    let disposed = false;

    const checkRelease = async () => {
      if (disposed || reloadAttempted.current || document.hidden) return;

      try {
        const response = await fetchWithCsrf(`/tag_version?t=${Date.now()}`, {
          method: "GET",
          cache: "no-store",
          credentials: "same-origin",
        });
        if (!response.ok || disposed) return;

        const deployedVersion = normalizeVersion(await response.text());
        if (
          !isUsableVersion(deployedVersion) ||
          deployedVersion === runtimeVersion
        ) {
          return;
        }

        const reloadKey = `${RELEASE_RELOAD_KEY_PREFIX}${runtimeVersion}->${deployedVersion}`;
        reloadAttempted.current = true;
        try {
          if (window.sessionStorage.getItem(reloadKey)) return;
          window.sessionStorage.setItem(reloadKey, "1");
        } catch {
          // The in-memory guard still prevents a reload loop when storage is
          // unavailable, for example in a hardened private browser window.
        }
        window.location.reload();
      } catch {
        // A release check must never make CRCON unavailable. The next focus or
        // interval retries after transient network errors.
      }
    };

    const checkWhenVisible = () => {
      if (!document.hidden) void checkRelease();
    };

    void checkRelease();
    const interval = window.setInterval(
      checkRelease,
      RELEASE_CHECK_INTERVAL_MS
    );
    window.addEventListener("focus", checkWhenVisible);
    document.addEventListener("visibilitychange", checkWhenVisible);

    return () => {
      disposed = true;
      window.clearInterval(interval);
      window.removeEventListener("focus", checkWhenVisible);
      document.removeEventListener("visibilitychange", checkWhenVisible);
    };
  }, []);
}
