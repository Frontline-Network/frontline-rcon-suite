const HLLV_IMAGE_SUFFIX_BY_NAME = new Map([
  ["van tuong", "a"],
  ["quang ngai", "b"],
  ["hue outskirts", "c"],
  ["dak to airfield", "d"],
  ["cam ranh port", "e"],
  ["thanh hoa bridge", "f"],
]);

const normalizeMapIdentifier = (value) =>
  String(value ?? "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/đ/g, "d");

const getLayerIdentifiers = (layer) => [
  layer?.image_name,
  layer?.id,
  layer?.name,
  layer?.pretty_name,
  layer?.map?.id,
  layer?.map?.name,
  layer?.map?.pretty_name,
  layer?.map?.shortname,
];

const getHllvImageSuffix = (layer) => {
  const identifiers = getLayerIdentifiers(layer).map(normalizeMapIdentifier);

  for (const identifier of identifiers) {
    const mapIdMatch = identifier.match(
      /(?:^|[^a-z0-9])wdev[_-]?([a-f])(?:[^a-z0-9]|$)/
    );
    if (mapIdMatch) return mapIdMatch[1];
  }

  for (const identifier of identifiers) {
    for (const [mapName, suffix] of HLLV_IMAGE_SUFFIX_BY_NAME) {
      if (identifier.includes(mapName)) return suffix;
    }
  }

  return null;
};

export const resolveMapImageName = (layer, fallback = null) => {
  const hllvSuffix = getHllvImageSuffix(layer);
  if (hllvSuffix) return `wdev_${hllvSuffix}-day.webp`;

  return layer?.image_name || fallback;
};

export const getMapImageSrc = (layer, fallback = null) => {
  const imageName = resolveMapImageName(layer, fallback);
  return imageName ? `/maps/${imageName}` : null;
};

export const getMapIconSrc = (layer, fallback = "unknown.webp") =>
  `/maps/icons/${resolveMapImageName(layer, fallback)}`;

export const resolveTacticalMapImageName = (layer, fallback = null) => {
  const hllvSuffix = getHllvImageSuffix(layer);
  if (hllvSuffix) return `wdev_${hllvSuffix}.webp`;

  const mapIdentifier = layer?.map?.id ?? layer?.map?.name;
  return mapIdentifier ? `${mapIdentifier}.webp` : fallback;
};

const HLL_LIVE_MAP_IDS = new Set([
  "carentan", "driel", "elalamein", "elsenbornridge", "foy", "hill400",
  "hurtgenforest", "junobeach", "kharkov", "kursk", "mortain", "omahabeach",
  "purpleheartlane", "remagen", "smolensk", "stalingrad", "stmariedumont",
  "stmereeglise", "tobruk", "utahbeach",
]);

export function getLiveMapArtwork(layer) {
  const vietnam = getHllvImageSuffix(layer);
  if (vietnam) {
    return {
      image: getTacticalMapImageSrc(layer),
      headquarters: `/live-maps/wdev_${vietnam}-hq.svg`,
      grid: false,
    };
  }
  const id = normalizeMapIdentifier(layer?.map?.id ?? layer?.map?.name);
  if (HLL_LIVE_MAP_IDS.has(id)) {
    return { image: `/live-maps/${id}.webp`, headquarters: null, grid: true };
  }
  return { image: getTacticalMapImageSrc(layer), headquarters: null, grid: false };
}

export const getTacticalMapImageSrc = (layer, fallback = null) => {
  const imageName = resolveTacticalMapImageName(layer, fallback);
  return imageName ? `/tac-maps/${imageName}` : null;
};
