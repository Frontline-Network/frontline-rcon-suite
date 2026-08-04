import { cmd } from "@/utils/fetchUtils"
import { demoMapLayers, isFakeMode } from "@/mirage/demo-data"

export const loader = async () => {
    if (isFakeMode()) {
      return {
        mapListStatus: demoMapLayers.map((map, index) => ({ map, voters: 12 - index * 3 })),
        config: { enabled: true },
      }
    }
    const mapListStatus = await cmd.GET_VOTEMAP_STATUS()
    const config = await cmd.GET_VOTEMAP_CONFIG()
    return { mapListStatus, config }
}
