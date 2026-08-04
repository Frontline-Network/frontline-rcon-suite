import { cmd } from "@/utils/fetchUtils"
import { isFakeMode } from "@/mirage/demo-data"

export const loader = async () => {
    if (isFakeMode()) return { serverName: "[GER] Frontline Network | #2", serverNameConfig: { enabled: false, public_name: "Frontline Network" } }
    const serverName = await cmd.GET_SERVER_NAME()
    const serverNameConfig = await cmd.GET_SERVER_NAME_CHANGE_CONFIG()
    return { serverName, serverNameConfig }
}
