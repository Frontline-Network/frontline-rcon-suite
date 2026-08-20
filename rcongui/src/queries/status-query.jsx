import {
  getDemoConnectionMode,
  getDemoServerStatus,
  isFakeMode,
} from "@/mirage/demo-data";
import { cmd } from "@/utils/fetchUtils";
import { queryOptions } from "@tanstack/react-query";

export const gameStatusQueryOptions = () =>
  queryOptions({
    queryKey: [{ queryIdentifier: "get_status" }],
    queryFn: async () => {
      if (
        isFakeMode() &&
        ["gameserver_offline", "gameserver_stale"].includes(
          getDemoConnectionMode()
        )
      ) {
        throw new Error("Demo game server is unavailable");
      }
      return isFakeMode()
        ? getDemoServerStatus()
        : cmd.GET_GAME_SERVER_STATUS();
    },
    initialData:
      isFakeMode() && getDemoConnectionMode() === "gameserver_stale"
        ? getDemoServerStatus()
        : undefined,
    staleTime: 15 * 1000,
    retry: 1,
  });
