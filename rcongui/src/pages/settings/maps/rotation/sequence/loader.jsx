import { cmd } from "@/utils/fetchUtils";
import { demoMapLayers, isFakeMode } from "@/mirage/demo-data";

export const loader = async () => {
  const sequence = isFakeMode()
    ? { maps: demoMapLayers, current_index: 0 }
    : await cmd.GET_MAP_SEQUENCE();
  return { sequence };
};
