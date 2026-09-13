export function normalizeLogDisplayPreferences(value) {
  return {
    fontSize: ["small", "normal", "large"].includes(value?.fontSize)
      ? value.fontSize
      : "small",
    density: ["dense", "normal", "comfortable"].includes(value?.density)
      ? value.density
      : "dense",
  };
}

export function getLogPresentation(value) {
  const { fontSize, density } = normalizeLogDisplayPreferences(value);
  return {
    fontSize: { small: "0.875rem", normal: "1rem", large: "1.15rem" }[fontSize],
    paddingY: { dense: 1, normal: 1.5, comfortable: 2 }[density],
  };
}

export function matchesLogActions(action, selected = []) {
  // Match the server's action-prefix contract, including CHAT subgroups and TK AUTO.
  return selected.some((candidate) =>
    String(action ?? "")
      .toLowerCase()
      .startsWith(candidate.toLowerCase())
  );
}

export const isValidLogQueryLimit = (value) =>
  String(value).trim() !== "" &&
  Number.isInteger(Number(value)) &&
  Number(value) >= 10 &&
  Number(value) <= 100_000;
