import { teamsLiveQueryOptions } from "@/queries/teams-live-query";
import { cmd } from "@/utils/fetchUtils";
import { queryOptions, useQueries, useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { create } from "zustand";
import {
  demoGameState,
  getDemoConnectionMode,
  getDemoServerConnection,
  getDemoServerList,
  getDemoServerStatus,
  isFakeMode,
} from "@/mirage/demo-data";
import {
  CONNECTION_STATE,
  createConnectionHealth,
  EMPTY_CONNECTION_HEALTH,
} from "@/utils/connectionHealth";

// Create the Zustand store
export const useGlobalStore = create((set) => ({
  // State
  serverState: null,
  status: null,
  servers: [],
  gameState: null,
  onlineIngameMods: [],
  onlineCrconMods: [],
  onlinePlayers: [],
  connectionHealth: {
    crcon: EMPTY_CONNECTION_HEALTH,
    gameServer: EMPTY_CONNECTION_HEALTH,
    gameState: EMPTY_CONNECTION_HEALTH,
  },
  // Actions to update state
  updateStatus: (data) => set(() => ({ status: data })),
  updateServerState: (data) => set(() => ({ serverState: data })),
  updateServers: (data) => set(() => ({ servers: data })),
  updateGameState: (data) => set(() => ({ gameState: data })),
  updateOnlineIngameMods: (data) => set(() => ({ onlineIngameMods: data })),
  updateOnlineCrconMods: (data) => set(() => ({ onlineCrconMods: data })),
  updateOnlinePlayers: (data) => set(() => ({ onlinePlayers: data })),
}));

const staleTime = 15 * 1000;
const refetchInterval = 30 * 1000;

// Define your global queries with onSuccess callbacks
const globalQueries = [
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
    retry: 1,
  }),
  queryOptions({
    queryKey: [{ queryIdentifier: "get_gamestate" }],
    queryFn: async () => {
      if (
        isFakeMode() &&
        ["gameserver_offline", "gameserver_stale"].includes(
          getDemoConnectionMode()
        )
      ) {
        throw new Error("Demo game state is unavailable");
      }
      return isFakeMode() ? demoGameState : cmd.GET_GAME_STATE();
    },
    initialData:
      isFakeMode() && getDemoConnectionMode() === "gameserver_stale"
        ? demoGameState
        : undefined,
  }),
  queryOptions({
    queryKey: [{ queryIdentifier: "get_server_list" }],
    queryFn: isFakeMode()
      ? () => Promise.resolve(getDemoServerList())
      : cmd.GET_GAME_SERVER_LIST,
  }),
  queryOptions({
    queryKey: [{ queryIdentifier: "get_ingame_mods" }],
    queryFn: isFakeMode() ? () => Promise.resolve([]) : cmd.GET_INGAME_MODS,
  }),
  queryOptions({
    queryKey: [{ queryIdentifier: "get_online_mods" }],
    queryFn: isFakeMode() ? () => Promise.resolve([]) : cmd.GET_CRCON_MODS,
  }),
  teamsLiveQueryOptions,
];

export const GlobalState = () => {
  const crconQuery = useQuery({
    queryKey: [{ queryIdentifier: "get_connection_info" }],
    queryFn: async () => {
      if (
        isFakeMode() &&
        ["crcon_offline", "crcon_stale"].includes(getDemoConnectionMode())
      ) {
        throw new Error("Demo CRCON is unavailable");
      }
      return isFakeMode()
        ? getDemoServerConnection()
        : cmd.GET_CRCON_SERVER_CONNECTION();
    },
    initialData:
      isFakeMode() && getDemoConnectionMode() === "crcon_stale"
        ? getDemoServerConnection()
        : undefined,
    refetchInterval,
    retry: isFakeMode() ? 0 : 1,
  });
  const crconHealth = createConnectionHealth(crconQuery);
  const canQueryGameServer = crconHealth.state === CONNECTION_STATE.ONLINE;

  const queryResults = useQueries({
    queries: globalQueries.map((query) =>
      queryOptions({
        staleTime,
        refetchInterval,
        enabled: canQueryGameServer,
        ...query,
      })
    ),
  });

  const statusQuery = queryResults[0];
  const gameStateQuery = queryResults[1];
  const serversQuery = queryResults[2];
  const ingameModsQuery = queryResults[3];
  const crconModsQuery = queryResults[4];

  useEffect(() => {
    useGlobalStore.setState({
      serverState: crconQuery.data ?? null,
      status: statusQuery?.data ?? null,
      gameState: gameStateQuery?.data ?? null,
      servers: serversQuery?.data ?? [],
      onlineIngameMods: ingameModsQuery?.data ?? [],
      onlineCrconMods: crconModsQuery?.data ?? [],
      onlinePlayers: canQueryGameServer
        ? useGlobalStore.getState().onlinePlayers
        : [],
      connectionHealth: {
        crcon: crconHealth,
        gameServer: createConnectionHealth(statusQuery, {
          enabled: canQueryGameServer,
        }),
        gameState: createConnectionHealth(gameStateQuery, {
          enabled: canQueryGameServer,
        }),
      },
    });
  }, [
    canQueryGameServer,
    crconHealth.state,
    crconHealth.lastSuccessAt,
    crconHealth.lastAttemptAt,
    crconHealth.isRefreshing,
    crconQuery.data,
    statusQuery?.data,
    statusQuery?.status,
    statusQuery?.fetchStatus,
    statusQuery?.dataUpdatedAt,
    statusQuery?.errorUpdatedAt,
    gameStateQuery?.data,
    gameStateQuery?.status,
    gameStateQuery?.fetchStatus,
    gameStateQuery?.dataUpdatedAt,
    gameStateQuery?.errorUpdatedAt,
    serversQuery?.data,
    ingameModsQuery?.data,
    crconModsQuery?.data,
  ]);

  return null;
};
