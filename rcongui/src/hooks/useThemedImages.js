import { useTheme } from "@mui/material"
import { getFactionIconSrc } from "@/utils/factionIcons";

const getLightRoleIconSrc = (role) => `/icons/roles/${role}.png`
const getDarkRoleIconSrc = (role) => `/icons/roles/${role}_black.png`
const getLightMetricIconSrc = (metric) => `/icons/metrics/${metric}.png`
const getDarkMetricIconSrc = (metric) => `/icons/metrics/${metric}_black.png`

export const useThemedImages = () => {
    const theme = useTheme()
    const mode = theme.palette.mode
    return {
        getFactionIconSrc: (faction) => getFactionIconSrc(faction, mode === "dark" ? "default" : "dark"),
        getRoleIconSrc: mode === "dark" ? getLightRoleIconSrc : getDarkRoleIconSrc,
        getMetricIconSrc: mode === "dark" ? getLightMetricIconSrc : getDarkMetricIconSrc,
    }
}
