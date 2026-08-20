import { cmd } from "@/utils/fetchUtils";
import { demoMapLayers, isFakeMode } from "@/mirage/demo-data";
import { gameStatusQueryOptions } from "@/queries/status-query";
import { queryClient } from "@/queryClient";
import { resolveTimerSettings } from "./timer-capabilities.mjs";

export const loader = async () => {
  const [maps, status] = await Promise.all([
    isFakeMode() ? demoMapLayers : cmd.GET_MAPS(),
    queryClient.ensureQueryData(gameStatusQueryOptions()),
  ]);

  return { timers: resolveTimerSettings(status), maps };
};
