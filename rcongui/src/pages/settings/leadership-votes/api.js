import { fetchWithCsrf, SESSION_EXPIRY_EVENT } from "@/utils/fetchUtils";
import { isFakeMode } from "@/mirage/demo-data";

export async function voteRequest(path, data, method = data ? "PUT" : "GET") {
  if (isFakeMode()) {
    const { demoRequest } = await import("./demo");
    return demoRequest(path, data, method);
  }
  const response = await fetchWithCsrf(`/api/leadership-vote/v1/${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    ...(data ? { body: JSON.stringify(data) } : {}),
  });
  if (response.status === 401)
    window.dispatchEvent(new Event(SESSION_EXPIRY_EVENT));
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload.failed) {
    const error = new Error(payload.error || `HTTP ${response.status}`);
    error.status = response.status;
    throw error;
  }
  return payload.result;
}
