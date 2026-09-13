import { cmd } from "@/utils/fetchUtils";
import { queryOptions } from "@tanstack/react-query";

import { getDemoConnectionMode, getDemoServerStatus } from "@/mirage/demo-data";

export const gameStatusQueryOptions = () =>
  queryOptions({
    queryKey: [{ queryIdentifier: "get_status" }],
    queryFn: async () => {
      if (
        import.meta.env.MODE === "fake" &&
        ["gameserver_offline", "gameserver_stale"].includes(
          getDemoConnectionMode()
        )
      ) {
        throw new Error("Demo game server is unavailable");
      }
      return import.meta.env.MODE === "fake"
        ? getDemoServerStatus()
        : cmd.GET_GAME_SERVER_STATUS();
    },
    initialData:
      import.meta.env.MODE === "fake" &&
      getDemoConnectionMode() === "gameserver_stale"
        ? getDemoServerStatus()
        : undefined,
    staleTime: 15 * 1000,
    retry: 1,
  });
