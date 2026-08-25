const FACTION_ASSETS = {
  us: "webp",
  ger: "webp",
  rus: "webp",
  gb: "webp",
  can: "webp",
  dak: "svg",
  cw: "svg",
  nva: "svg",
};

const aliases = {
  allies: "us",
  axis: "ger",
  british: "gb",
  commonwealth: "gb",
  cw: "gb",
  dak: "ger",
  german: "ger",
  germany: "ger",
  northvietnam: "nva",
  "north-vietnam": "nva",
  pavn: "nva",
  vietcong: "nva",
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
  const extension = FACTION_ASSETS[key];

  if (extension) {
    return `/icons/teams/${key}${suffix}.${extension}`;
  }
  return `/icons/teams/unknown${suffix}.svg`;
};
