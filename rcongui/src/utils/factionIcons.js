const OFFICIAL_FACTIONS = new Set(["us", "ger", "rus", "gb", "can"]);

const aliases = {
  allies: "us",
  axis: "ger",
  british: "gb",
  commonwealth: "gb",
  cw: "gb",
  dak: "ger",
  german: "ger",
  germany: "ger",
  soviet: "rus",
  soviets: "rus",
  ussr: "rus",
  "afrika-korps": "ger",
  "deutsches-afrikakorps": "ger",
};

export const normalizeFaction = (faction) => {
  const value = String(faction ?? "")
    .trim()
    .toLowerCase()
    .replace(/[\s_]+/g, "-");
  return aliases[value] ?? value;
};

export const getFactionIconSrc = (faction, variant = "default") => {
  const key = normalizeFaction(faction);
  const suffix = variant === "default" ? "" : `_${variant}`;

  if (OFFICIAL_FACTIONS.has(key)) {
    return `/icons/teams/${key}${suffix}.webp`;
  }
  return `/icons/teams/unknown${suffix}.svg`;
};
