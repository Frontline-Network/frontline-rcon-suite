const OFFICIAL_FACTIONS = new Set(["us", "ger", "rus", "gb", "can"]);
const LOCAL_FACTIONS = new Set(["cw", "dak"]);

const aliases = {
  allies: "us",
  axis: "ger",
  british: "gb",
  commonwealth: "cw",
  german: "ger",
  germany: "ger",
  soviet: "rus",
  soviets: "rus",
  ussr: "rus",
  "afrika-korps": "dak",
  "deutsches-afrikakorps": "dak",
};

export const normalizeFaction = (faction) => {
  const value = String(faction ?? "").trim().toLowerCase();
  return aliases[value] ?? value;
};

export const getFactionIconSrc = (faction, variant = "default") => {
  const key = normalizeFaction(faction);
  const suffix = variant === "default" ? "" : `_${variant}`;

  if (LOCAL_FACTIONS.has(key)) {
    return `/icons/teams/${key}${suffix}.svg`;
  }
  if (OFFICIAL_FACTIONS.has(key)) {
    return `/icons/teams/${key}${suffix}.webp`;
  }
  return `/icons/teams/unknown${suffix}.svg`;
};
