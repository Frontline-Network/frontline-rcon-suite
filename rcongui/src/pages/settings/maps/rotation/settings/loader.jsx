import { cmd } from "@/utils/fetchUtils"
import { demoMapLayers, isFakeMode } from "@/mirage/demo-data"

export const loader = async () => {
    if (isFakeMode()) {
      return {
        shuffleEnabled: false,
        rotation: { maps: demoMapLayers, current_index: 0, next_index: 1 },
      }
    }
    const [shuffleEnabled, rotation] = await Promise.all([
      cmd.GET_MAP_ROTATION_SHUFFLE(),
      cmd.GET_MAP_ROTATION(),
    ])
    return { shuffleEnabled, rotation }
}
