import { cmd } from "@/utils/fetchUtils"
import { demoMapLayers, isFakeMode } from "@/mirage/demo-data"
import { unifiedGamemodeName } from "./helpers"

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
    const gameState = await cmd.GET_GAME_STATE()
    if (unifiedGamemodeName(gameState.current_map.game_mode) === "skirmish") {
      throw new Error("skirmish")
    }
    const objectives = await cmd.GET_MAP_OBJECTIVES()
    return { objectives, gameState }
}
