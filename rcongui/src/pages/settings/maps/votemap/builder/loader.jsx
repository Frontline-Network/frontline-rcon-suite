import { cmd } from "@/utils/fetchUtils";
import { demoMapLayers, isFakeMode } from "@/mirage/demo-data";

export const loader = async () => {
  const whitelist = isFakeMode()
    ? demoMapLayers.slice(0, 2).map((map) => map.id)
    : await cmd.GET_VOTEMAP_WHITELIST();

  return { whitelist };
};
