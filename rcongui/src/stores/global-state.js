import { teamsLiveQueryOptions } from "@/queries/teams-live-query";
import { cmd } from "@/utils/fetchUtils";
import { queryOptions, useQueries, useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { create } from "zustand";
import {
  demoGameState,
  demoServerConnection,
  demoServerStatus,
  isFakeMode,
} from "@/mirage/demo-data";
import {
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

// Define the globally shared API queries. Their data and transport health are
// mirrored into Zustand together in GlobalState below.
const globalQueries = [
  queryOptions({
    queryKey: [{ queryIdentifier: "get_status" }],
    queryFn: isFakeMode()
      ? () => Promise.resolve(demoServerStatus)
      : cmd.GET_GAME_SERVER_STATUS,
    retry: 1,
  }),
  queryOptions({
    queryKey: [{ queryIdentifier: "get_gamestate" }],
    queryFn: isFakeMode()
      ? () => Promise.resolve(demoGameState)
      : cmd.GET_GAME_STATE,
  }),
  queryOptions({
    queryKey: [{ queryIdentifier: "get_server_list" }],
    queryFn: isFakeMode()
      ? () => Promise.resolve([])
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
    queryFn: isFakeMode()
      ? () => Promise.resolve(demoServerConnection)
      : cmd.GET_CRCON_SERVER_CONNECTION,
    refetchInterval,
    retry: 1,
  });
  const crconHealth = createConnectionHealth(crconQuery);
  const canQueryGameServer = Boolean(crconQuery.data);

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
    const gameServerHealth = createConnectionHealth(statusQuery, {
      enabled: canQueryGameServer,
    });
    const gameStateHealth = createConnectionHealth(gameStateQuery, {
      enabled: canQueryGameServer,
    });

    useGlobalStore.setState({
      serverState: crconQuery.data ?? null,
      status: statusQuery?.data ?? null,
      gameState: gameStateQuery?.data ?? null,
      servers: serversQuery?.data ?? [],
      onlineIngameMods: ingameModsQuery?.data ?? [],
      onlineCrconMods: crconModsQuery?.data ?? [],
      connectionHealth: {
        crcon: crconHealth,
        gameServer: gameServerHealth,
        gameState: gameStateHealth,
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
