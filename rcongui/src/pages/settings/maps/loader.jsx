import { cmd } from "@/utils/fetchUtils"
import { demoMapLayers, isFakeMode } from "@/mirage/demo-data"

export const loader = async () => {
    const maps = isFakeMode() ? demoMapLayers : await cmd.GET_MAPS()
    return { maps }    
}
