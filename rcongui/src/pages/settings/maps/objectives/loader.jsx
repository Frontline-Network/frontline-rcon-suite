import { cmd } from "@/utils/fetchUtils"
import { demoMapLayers, isFakeMode } from "@/mirage/demo-data"
import { unifiedGamemodeName } from "./helpers"
import { gameStatusQueryOptions } from "@/queries/status-query"
import { queryClient } from "@/queryClient"
import { resolveSectorLayoutCapabilities } from "./layout-capabilities.mjs"

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
    const [gameState, status] = await Promise.all([
      cmd.GET_GAME_STATE(),
      queryClient.ensureQueryData(gameStatusQueryOptions()),
    ])
    if (unifiedGamemodeName(gameState.current_map.game_mode) === "skirmish") {
      throw new Error("skirmish")
    }
    const sectorLayout = resolveSectorLayoutCapabilities(status)
    if (!sectorLayout.read) {
      return { objectives: null, gameState, sectorLayout }
    }
    const objectives = await cmd.GET_MAP_OBJECTIVES()
    return { objectives, gameState, sectorLayout }
}
