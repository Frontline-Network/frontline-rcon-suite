import { cmd } from "@/utils/fetchUtils"
import { demoMapLayers, isFakeMode } from "@/mirage/demo-data"

export const loader = async () => {
    const rotation = isFakeMode()
      ? { maps: demoMapLayers, current_index: 0, next_index: 1 }
      : await cmd.GET_MAP_ROTATION()
    return { rotation }
}
