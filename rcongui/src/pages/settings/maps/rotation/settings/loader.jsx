import { cmd } from "@/utils/fetchUtils"
import { isFakeMode } from "@/mirage/demo-data"

export const loader = async () => {
    const shuffleEnabled = isFakeMode() ? false : await cmd.GET_MAP_ROTATION_SHUFFLE()
    return { shuffleEnabled }
}
