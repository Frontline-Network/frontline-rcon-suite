// Preview-only persistence. Real installations store this in the user database.
const key = "crcon.preview.highlights:v0.8.8:preview-user";
let memory = null;

export function previewHighlightState() {
  let value = memory;
  try {
    value = JSON.parse(localStorage.getItem(key)) || value;
  } catch {
    /* Memory fallback. */
  }
  return {
    release_version: "v0.8.8",
    seen: Boolean(value?.seen),
    snoozed_until: value?.snoozed_until || null,
    auto_show:
      !value?.seen &&
      (!value?.snoozed_until || Date.parse(value.snoozed_until) <= Date.now()),
  };
}

export function updatePreviewHighlightState(action) {
  const previous = previewHighlightState();
  const show = action === "claim" && previous.auto_show;
  if (action !== "claim" || show) {
    memory = {
      seen: action !== "later",
      snoozed_until:
        action === "later"
          ? new Date(Date.now() + 86_400_000).toISOString()
          : null,
    };
    try {
      localStorage.setItem(key, JSON.stringify(memory));
    } catch {
      /* Memory fallback. */
    }
  }
  return { ...previewHighlightState(), show };
}
