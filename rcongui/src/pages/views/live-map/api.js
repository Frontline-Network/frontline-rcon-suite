import { fetchWithCsrf, SESSION_EXPIRY_EVENT } from "@/utils/fetchUtils";
import { isFakeMode } from "@/mirage/demo-data";
import i18n from "@/i18n";
import { translateOperatorMessage } from "@/i18n/operator-messages";

export async function liveMapRequest(
  path,
  data,
  method = data ? "POST" : "GET"
) {
  if (isFakeMode()) {
    const { demoRequest } = await import("./demo");
    return demoRequest(path, data, method);
  }
  const response = await fetchWithCsrf(`/api/live-map/v1/${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    ...(data ? { body: JSON.stringify(data) } : {}),
  });
  if (response.status === 401)
    window.dispatchEvent(new Event(SESSION_EXPIRY_EVENT));
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload.failed) {
    const error = new Error(
      payload.error
        ? translateOperatorMessage(payload.error, i18n.t.bind(i18n))
        : i18n.t("liveViews.requestFailed", { status: response.status })
    );
    error.status = response.status;
    throw error;
  }
  return payload.result;
}

export const canUse = (permissions, permission) =>
  Boolean(
    permissions?.is_superuser ||
      permissions?.permissions?.some((p) => p.permission === permission)
  );
