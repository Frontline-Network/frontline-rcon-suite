export const HTTP_ERROR_TOAST_BUDGET = 3;
export const HTTP_ERROR_TOAST_WINDOW_MS = 60_000;

// This deliberately stores only a stable, sanitized error signature. API
// payloads may contain operational or player data and must not end up in a
// global notification or browser-memory diagnostic history.
export const createHttpErrorToastBudget = () => {
  const active = new Map();
  const diagnostics = [];

  const prune = (now) => {
    for (const [signature, state] of active.entries()) {
      if (now - state.lastSeen > HTTP_ERROR_TOAST_WINDOW_MS) {
        active.delete(signature);
      }
    }
  };

  const recordDiagnostic = (signature, now) => {
    const previous = diagnostics.find(
      (diagnostic) => diagnostic.signature === signature
    );
    if (previous) {
      previous.count += 1;
      previous.lastSeen = now;
      return;
    }

    diagnostics.push({ signature, count: 1, firstSeen: now, lastSeen: now });
    if (diagnostics.length > 25) diagnostics.shift();
  };

  return {
    record(signature, now = Date.now()) {
      prune(now);
      recordDiagnostic(signature, now);

      const previous = active.get(signature);
      if (previous) {
        previous.count += 1;
        previous.lastSeen = now;
        return { kind: "repeat", count: previous.count };
      }

      active.set(signature, { count: 1, lastSeen: now });
      if (active.size <= HTTP_ERROR_TOAST_BUDGET) {
        return { kind: "new", count: 1 };
      }

      return {
        kind: "suppressed",
        suppressed: active.size - HTTP_ERROR_TOAST_BUDGET,
      };
    },
    diagnostics() {
      return diagnostics.map((diagnostic) => ({ ...diagnostic }));
    },
  };
};
