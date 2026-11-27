import { get, execute } from "@/utils/fetchUtils";

export async function result(response) {
  const data = await response.json();
  if (data.failed || data.error) throw new Error(typeof data.error === "string" ? data.error : JSON.stringify(data.error));
  return data.result;
}
export const read = (command, params = {}) => get(command + (Object.keys(params).length ? "?" + new URLSearchParams(params) : "")).then(result);
export const write = (command, payload) => execute(command, payload).then(result);
export const allowed = (permissions, name) => !!permissions?.is_superuser || !!permissions?.permissions?.some(p => p.permission === name);
