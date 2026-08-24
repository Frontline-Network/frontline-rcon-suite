const EMPTY_LABEL = "–";

const capitalizeWords = (value) =>
  value.replace(/(^|[\s/_-])(\p{L})/gu, (_match, separator, letter) =>
    `${separator}${letter.toLocaleUpperCase()}`
  );

const humanizeIdentifier = (value) =>
  capitalizeWords(
    value
      .replace(/([a-z\d])([A-Z])/g, "$1 $2")
      .replace(/[\s/_-]+/g, " ")
      .trim()
  );

export const formatSquadLabel = (value) => {
  const normalized = String(value ?? "").trim();
  return normalized ? capitalizeWords(normalized) : EMPTY_LABEL;
};

export const formatRoleLabel = (t, value) => {
  const rawValue = String(value ?? "").trim();
  if (!rawValue) return EMPTY_LABEL;

  return t(`settings.configForms.roles.${rawValue.toLowerCase()}`, {
    defaultValue: humanizeIdentifier(rawValue),
  });
};
