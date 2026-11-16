const memory = new Map();
const shadowed = new Set();
const listeners = new Set();
let unavailable = false;

function reportUnavailable() {
  if (unavailable) return;
  unavailable = true;
  queueMicrotask(() => listeners.forEach((listener) => listener()));
}

export const storageIsUnavailable = () => unavailable;
export function subscribeStorageAvailability(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export const browserStorage = {
  getItem(key) {
    if (shadowed.has(key)) return memory.get(key) ?? null;
    try { return window.localStorage.getItem(key); }
    catch { reportUnavailable(); return memory.get(key) ?? null; }
  },
  setItem(key, value) {
    try {
      window.localStorage.setItem(key, value);
      shadowed.delete(key);
      memory.delete(key);
    } catch {
      memory.set(key, String(value));
      shadowed.add(key);
      reportUnavailable();
    }
  },
  removeItem(key) {
    try {
      window.localStorage.removeItem(key);
      shadowed.delete(key);
      memory.delete(key);
    } catch {
      memory.delete(key);
      shadowed.add(key);
      reportUnavailable();
    }
  },
};
