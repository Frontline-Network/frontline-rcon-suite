import { faPlaystation } from "@fortawesome/free-brands-svg-icons/faPlaystation";
import { faSteam } from "@fortawesome/free-brands-svg-icons/faSteam";
import { faXbox } from "@fortawesome/free-brands-svg-icons/faXbox";
import { faGamepad } from "@fortawesome/free-solid-svg-icons/faGamepad";
import { normalizePlatform, PLATFORM_LABELS, platformLabel } from "@/utils/player-identity.mjs";

export const PLATFORMS = {
  STEAM: "steam",
  EPIC: "epic",
  XBOX_LIVE: "xbl",
  XBOX_SERIES_X: "xsx",
  PLAYSTATION_NETWORK: "psn",
  PLAYSTATION_5: "ps5",
};

export const PLATFORMS_TO_ICON = {
  [PLATFORMS.STEAM]: faSteam,
  [PLATFORMS.EPIC]: faGamepad,
  [PLATFORMS.XBOX_LIVE]: faXbox,
  [PLATFORMS.XBOX_SERIES_X]: faXbox,
  [PLATFORMS.PLAYSTATION_NETWORK]: faPlaystation,
  [PLATFORMS.PLAYSTATION_5]: faPlaystation,
};

export const PLATFORMS_TO_LABELS = PLATFORM_LABELS;

export const getAllPlatforms = () => [
  {
    value: PLATFORMS.STEAM,
    label: PLATFORMS_TO_LABELS[PLATFORMS.STEAM],
    icon: PLATFORMS_TO_ICON[PLATFORMS.STEAM],
  },
  {
    value: PLATFORMS.EPIC,
    label: PLATFORMS_TO_LABELS[PLATFORMS.EPIC],
    icon: PLATFORMS_TO_ICON[PLATFORMS.EPIC],
  },
  {
    value: PLATFORMS.XBOX_LIVE,
    label: PLATFORMS_TO_LABELS[PLATFORMS.XBOX_LIVE],
    icon: PLATFORMS_TO_ICON[PLATFORMS.XBOX_LIVE],
  },
  {
    value: PLATFORMS.XBOX_SERIES_X,
    label: PLATFORMS_TO_LABELS[PLATFORMS.XBOX_SERIES_X],
    icon: PLATFORMS_TO_ICON[PLATFORMS.XBOX_SERIES_X],
  },
  {
    value: PLATFORMS.PLAYSTATION_NETWORK,
    label: PLATFORMS_TO_LABELS[PLATFORMS.PLAYSTATION_NETWORK],
    icon: PLATFORMS_TO_ICON[PLATFORMS.PLAYSTATION_NETWORK],
  },
  {
    value: PLATFORMS.PLAYSTATION_5,
    label: PLATFORMS_TO_LABELS[PLATFORMS.PLAYSTATION_5],
    icon: PLATFORMS_TO_ICON[PLATFORMS.PLAYSTATION_5],
  },
];

export const getPlatformLabel = platformLabel;

export const getPlatformIcon = (platformValue) => {
  return PLATFORMS_TO_ICON[normalizePlatform(platformValue)] || faGamepad;
};

// Preserve server-provided values when editing other soldier fields, but
// render their friendly label rather than a blank/out-of-range select.
export const getPlatformOptions = (currentValue) => {
  const options = getAllPlatforms();
  if (currentValue && !options.some(({ value }) => value === currentValue)) {
    options.push({ value: currentValue, label: getPlatformLabel(currentValue) });
  }
  return options;
};
