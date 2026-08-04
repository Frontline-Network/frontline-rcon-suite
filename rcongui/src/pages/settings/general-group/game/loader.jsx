import { cmd } from "@/utils/fetchUtils";
import { demoMapLayers, isFakeMode } from "@/mirage/demo-data";

export const loader = async () => {
    const maps = isFakeMode() ? demoMapLayers : await cmd.GET_MAPS();
    const timers = {
        match: {
            warfare: {
                min: 30,
                max: 180,
                default: 90,
            },
            offensive: {
                min: 10,
                max: 60,
                default: 30,
            },
            skirmish: {
                min: 10,
                max: 60,
                default: 30,
            },
        },
        warmup: {
            warfare: {
                min: 1,
                max: 10,
                default: 3,
            },
            skirmish: {
                min: 1,
                max: 10,
                default: 3,
            },
        },
    }
    return { timers, maps }
}
