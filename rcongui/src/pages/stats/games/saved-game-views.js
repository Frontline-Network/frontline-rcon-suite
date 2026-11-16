import { browserStorage } from "@/utils/browser-storage";

const STORAGE_KEY = "frontline.stats.games.saved-views.v1";
const MAX_SAVED_VIEWS = 12;
const VALID_PERIODS = new Set(["all", "7", "30"]);

const normalizedString = (value, fallback = "") =>
  typeof value === "string" ? value : fallback;

export const normalizeGameViewFilters = (value = {}) => ({
  search: normalizedString(value.search).slice(0, 120),
  period: VALID_PERIODS.has(String(value.period))
    ? String(value.period)
    : "all",
  environment: normalizedString(value.environment, "all") || "all",
  mode: normalizedString(value.mode, "all") || "all",
});

export const areGameViewFiltersEqual = (left, right) => {
  const normalizedLeft = normalizeGameViewFilters(left);
  const normalizedRight = normalizeGameViewFilters(right);
  return Object.keys(normalizedLeft).every(
    (key) => normalizedLeft[key] === normalizedRight[key]
  );
};

export const sanitizeSavedGameViews = (value) =>
  (Array.isArray(value) ? value : [])
    .filter((entry) => entry && typeof entry === "object")
    .map((entry, index) => ({
      id:
        normalizedString(entry.id).trim() ||
        `legacy-${index}-${normalizedString(entry.name).trim()}`,
      name: normalizedString(entry.name).trim().slice(0, 40),
      filters: normalizeGameViewFilters(entry.filters),
    }))
    .filter((entry) => entry.name)
    .slice(0, MAX_SAVED_VIEWS);

export const loadSavedGameViews = () => {
  if (typeof window === "undefined") return [];
  try {
    return sanitizeSavedGameViews(
      JSON.parse(browserStorage.getItem(STORAGE_KEY) || "[]")
    );
  } catch {
    return [];
  }
};

export const persistSavedGameViews = (views) => {
  const sanitized = sanitizeSavedGameViews(views);
  if (typeof window === "undefined") return sanitized;
  try {
    browserStorage.setItem(STORAGE_KEY, JSON.stringify(sanitized));
  } catch {
    // The archive remains usable when private browsing or storage policies
    // block persistence. The in-memory state is kept for the current visit.
  }
  return sanitized;
};

const createViewId = () => {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `view-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
};

export const upsertSavedGameView = (views, name, filters) => {
  const normalizedName = normalizedString(name).trim().slice(0, 40);
  if (!normalizedName) return sanitizeSavedGameViews(views);

  const sanitized = sanitizeSavedGameViews(views);
  const existing = sanitized.find(
    (entry) =>
      entry.name.toLocaleLowerCase() === normalizedName.toLocaleLowerCase()
  );
  const nextEntry = {
    id: existing?.id || createViewId(),
    name: normalizedName,
    filters: normalizeGameViewFilters(filters),
  };

  return [
    nextEntry,
    ...sanitized.filter((entry) => entry.id !== nextEntry.id),
  ].slice(0, MAX_SAVED_VIEWS);
};

export const removeSavedGameView = (views, id) =>
  sanitizeSavedGameViews(views).filter((entry) => entry.id !== id);
