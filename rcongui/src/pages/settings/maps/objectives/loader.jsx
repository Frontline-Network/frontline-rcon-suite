import { cmd } from "@/utils/fetchUtils"
import { demoMapLayers, isFakeMode } from "@/mirage/demo-data"

export const loader = async () => {
    if (isFakeMode()) {
      return {
        objectives: [
          ["Road to Recourt", "Southern Edge", "Dugout Barn"],
          ["Foy", "West Bend", "Cobru Factory"],
          ["Flak Position", "Eastern Ourthe", "Bizory-Foy Road"],
          ["N30 Highway", "Train Line", "Foy Outskirts"],
          ["Cobru Approach", "Foy Road", "Forest Outskirts"],
        ],
        gameState: { current_map: demoMapLayers[0], next_map: demoMapLayers[1] },
      }
    }
    const objectives = await cmd.GET_MAP_OBJECTIVES()
    const gameState = await cmd.GET_GAME_STATE()
    return { objectives, gameState }
}
