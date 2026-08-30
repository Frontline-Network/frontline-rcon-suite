import { cmd } from "@/utils/fetchUtils";
import { demoMapLayers, isFakeMode } from "@/mirage/demo-data";

export const loader = async () => {
  if (isFakeMode()) {
    return {
      maps: demoMapLayers,
      whitelist: demoMapLayers.slice(0, 2).map((map) => map.id),
    };
  }

  const [maps, whitelist] = await Promise.all([
    cmd.GET_MAPS(),
    cmd.GET_VOTEMAP_WHITELIST(),
  ]);

  return { maps, whitelist };
};
