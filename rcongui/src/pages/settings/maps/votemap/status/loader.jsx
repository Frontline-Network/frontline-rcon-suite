import { cmd } from "@/utils/fetchUtils";
import { demoMapLayers, isFakeMode } from "@/mirage/demo-data";

export const loader = async () => {
  if (isFakeMode()) {
    return {
      votemapStatus: demoMapLayers.map((map, index) => ({
        map,
        voters: [],
        votes: 12 - index * 3,
      })),
      votemapResults: [],
    };
  }
  const votemapStatus = await cmd.GET_VOTEMAP_STATUS();
  const votemapResults = await cmd.GET_VOTEMAP_RESULTS();
  return { votemapStatus, votemapResults };
};
