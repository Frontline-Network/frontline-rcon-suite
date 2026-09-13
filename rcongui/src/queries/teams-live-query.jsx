import { useGlobalStore } from "@/stores/global-state";
import { extractPlayers } from "@/utils/extractPlayers";
import { cmd } from "@/utils/fetchUtils";
import { normalizePlayerProfile } from "@/utils/lib";
import { useQuery } from "@tanstack/react-query";
import { getDemoTeamView } from "@/mirage/demo-data";

let previousTeamView;
let previousOnlinePlayers = [];

const getNormalizedOnlinePlayers = (data) => {
  if (data === previousTeamView) return previousOnlinePlayers;

  previousTeamView = data;
  previousOnlinePlayers = extractPlayers(data).map((player) => ({
    ...player,
    profile: normalizePlayerProfile(player?.profile ?? {}),
  }));
  return previousOnlinePlayers;
};

export const teamsLiveQueryOptions = {
  queryKey: [{ queryIdentifier: "get_team_view" }],
  queryFn:
    import.meta.env.MODE === "fake"
      ? () => Promise.resolve(getDemoTeamView())
      : cmd.GET_LIVE_TEAMS,
  select: (data) => {
    // Think of this as a middleware that transforms the player data
    // in case the API returns something different than what we expect
    const onlinePlayers = getNormalizedOnlinePlayers(data);
    if (useGlobalStore.getState().onlinePlayers !== onlinePlayers) {
      useGlobalStore.setState({ onlinePlayers });
    }
    return data;
  },
};

export const teamsLiveQuery = (options) => {
  return useQuery({
    ...teamsLiveQueryOptions,
    ...options,
  });
};
