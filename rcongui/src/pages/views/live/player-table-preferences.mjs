export const PLAYER_COLUMN_GROUPS = {
  identity: {
    select: "views.table.selection",
    details: "common.details",
    player_summary: "views.table.playerSummary",
    team: "views.table.team",
    unit: "views.table.unit",
    role: "views.table.role",
    level: "views.table.level",
    platform: "views.table.platform",
    "clan-tag": "views.table.clanTag",
    name: "views.table.nameOnly",
    player_id: "views.table.playerId",
    country: "views.table.country",
  },
  performance: {
    kills: "views.table.kills",
    deaths: "views.table.deaths",
    kpm: "views.table.killsPerMinute",
    team_kills: "views.table.teamKills",
    combat: "views.table.combat",
    offense: "views.table.offense",
    defense: "views.table.defense",
    support: "views.table.support",
    vehicle_kills: "views.table.vehicleKills",
    vehicles_destroyed: "views.table.vehiclesDestroyed",
    performance_summary: "views.live.performance",
  },
  moderation: {
    status_summary: "views.live.status",
    active_ban: "views.table.activeBan",
    warnings: "views.table.warnings",
    watchlist: "views.table.watchlist",
    vip: "views.table.vip",
    flags: "views.table.flags",
    visits: "views.table.visits",
    time: "views.table.currentPlaytime",
    actions: "common.actions",
  },
};
export const PLAYER_COLUMN_IDS = Object.values(PLAYER_COLUMN_GROUPS).flatMap(
  Object.keys
);
export const FIXED_PLAYER_COLUMNS = [
  "select",
  "details",
  "player_summary",
  "actions",
];
const OPERATIONS_COLUMNS = new Set([
  ...FIXED_PLAYER_COLUMNS,
  "team",
  "unit",
  "kills",
  "deaths",
  "team_kills",
  "status_summary",
  "time",
]);
const operationsVisibility = () =>
  Object.fromEntries(
    PLAYER_COLUMN_IDS.map((id) => [id, OPERATIONS_COLUMNS.has(id)])
  );

export function normalizePlayerTablePreferences(value) {
  const defaults = operationsVisibility();
  return {
    preset: ["operations", "all", "custom"].includes(value?.preset)
      ? value.preset
      : "operations",
    fontSize: ["small", "normal", "large"].includes(value?.fontSize)
      ? value.fontSize
      : "small",
    density: ["dense", "normal", "comfortable"].includes(value?.density)
      ? value.density
      : "dense",
    columnVisibility: Object.fromEntries(
      PLAYER_COLUMN_IDS.map((id) => [
        id,
        FIXED_PLAYER_COLUMNS.includes(id)
          ? true
          : typeof value?.columnVisibility?.[id] === "boolean"
          ? value.columnVisibility[id]
          : defaults[id],
      ])
    ),
  };
}

export function getPlayerColumnVisibility(value) {
  const settings = normalizePlayerTablePreferences(value);
  if (settings.preset === "custom") return settings.columnVisibility;
  if (settings.preset === "operations") return operationsVisibility();
  // Keep the established expert preset without duplicate names/summary columns.
  return Object.fromEntries(
    PLAYER_COLUMN_IDS.map((id) => [
      id,
      !["player_id", "name", "performance_summary", "status_summary"].includes(
        id
      ),
    ])
  );
}

export function setPlayerColumnVisible(value, id, visible) {
  const settings = normalizePlayerTablePreferences(value);
  if (!PLAYER_COLUMN_IDS.includes(id) || FIXED_PLAYER_COLUMNS.includes(id))
    return settings;
  return {
    ...settings,
    preset: "custom",
    columnVisibility: {
      ...getPlayerColumnVisibility(settings),
      [id]: Boolean(visible),
    },
  };
}

export function getPlayerTablePresentation(value) {
  const { fontSize, density } = normalizePlayerTablePreferences(value);
  return {
    fontSize: { small: "0.85rem", normal: "1rem", large: "1.15rem" }[fontSize],
    rowHeight: Math.max(
      { dense: 38, normal: 46, comfortable: 56 }[density],
      fontSize === "large" ? 44 : 0
    ),
  };
}
