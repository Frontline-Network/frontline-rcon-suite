import { cmd } from "@/utils/fetchUtils"
import { isFakeMode } from "@/mirage/demo-data"

export const loader = async () => {
    const cameraConfig = isFakeMode() ? { enabled: true, discord_webhook_url: "https://discord.example/frontline" } : await cmd.GET_CAMERA_NOTIFICATION_CONFIG()
    return { cameraConfig }
}
