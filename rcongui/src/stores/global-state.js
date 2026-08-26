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
  isFakeMode,
} from "@/mirage/demo-data";
import { gameStatusQueryOptions } from "@/queries/status-query";
import {
  CONNECTION_STATE,
  createAggregateConnectionHealth,
  createConnectionHealth,
  EMPTY_CONNECTION_HEALTH,
} from "@/utils/connectionHealth";
import { useLocation } from "react-router-dom";
import {
  getGameStatePollingInterval,
  shouldPollLiveRoster,
  shouldPollModeratorPresence,
} from "@/queries/polling-policy";

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
    gameData: EMPTY_CONNECTION_HEALTH,
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
const defaultRefetchInterval = 30 * 1000;
const demoHealthLastAttemptAt = Date.now();
const demoHealthLastSuccessAt = demoHealthLastAttemptAt - 30_000;

const applyDemoHealth = (health, target) => {
  if (!isFakeMode()) return health;

  const mode = getDemoConnectionMode();
  const lastSuccessAt = health.lastSuccessAt || demoHealthLastSuccessAt;
  const lastAttemptAt = health.lastAttemptAt || demoHealthLastAttemptAt;

  if (target === "crcon") {
    if (mode === "crcon_offline") {
      return { ...health, state: CONNECTION_STATE.OFFLINE };
    }
    if (mode === "crcon_stale") {
      return {
        ...health,
        state: CONNECTION_STATE.STALE,
        lastSuccessAt,
        lastAttemptAt,
      };
    }
  }

  if (target === "gameServer") {
    if (["crcon_offline", "crcon_stale"].includes(mode)) {
      return { ...health, state: CONNECTION_STATE.UNKNOWN };
    }
    if (mode === "gameserver_offline") {
      return { ...health, state: CONNECTION_STATE.OFFLINE };
    }
    if (mode === "gameserver_stale") {
      return {
        ...health,
        state: CONNECTION_STATE.STALE,
        lastSuccessAt,
        lastAttemptAt,
      };
    }
  }

  if (target === "gameState") {
    if (["crcon_offline", "crcon_stale"].includes(mode)) {
      return { ...health, state: CONNECTION_STATE.UNKNOWN };
    }
    if (["gameserver_offline", "game_state_offline"].includes(mode)) {
      return { ...health, state: CONNECTION_STATE.OFFLINE };
    }
    if (["gameserver_stale", "game_state_stale"].includes(mode)) {
      return {
        ...health,
        state: CONNECTION_STATE.STALE,
        lastSuccessAt,
        lastAttemptAt,
      };
    }
  }

  return health;
};

// Define your global queries with onSuccess callbacks
const globalQueries = [
  gameStatusQueryOptions(),
  queryOptions({
    queryKey: [{ queryIdentifier: "get_gamestate" }],
    queryFn: async () => {
      if (
        isFakeMode() &&
        [
          "gameserver_offline",
          "gameserver_stale",
          "game_state_offline",
          "game_state_stale",
        ].includes(getDemoConnectionMode())
      ) {
        throw new Error("Demo game state is unavailable");
      }
      return isFakeMode() ? demoGameState : cmd.GET_GAME_STATE();
    },
    initialData:
      isFakeMode() &&
      ["gameserver_stale", "game_state_stale"].includes(getDemoConnectionMode())
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
  const location = useLocation();
  const gameStateRefetchInterval = getGameStatePollingInterval(
    location.pathname
  );
  const pollLiveRoster = shouldPollLiveRoster(location.pathname);
  const pollModeratorPresence = shouldPollModeratorPresence(location.pathname);
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
    refetchInterval: defaultRefetchInterval,
    retry: isFakeMode() ? 0 : 1,
  });
  const crconHealth = applyDemoHealth(
    createConnectionHealth(crconQuery),
    "crcon"
  );
  const canQueryGameServer = crconHealth.state === CONNECTION_STATE.ONLINE;

  const queryResults = useQueries({
    queries: globalQueries.map((query) => {
      const queryIdentifier = query.queryKey?.[0]?.queryIdentifier;
      const routeAllowsQuery =
        queryIdentifier === "get_team_view"
          ? pollLiveRoster
          : ["get_ingame_mods", "get_online_mods"].includes(queryIdentifier)
            ? pollModeratorPresence
            : true;
      return queryOptions({
        staleTime,
        refetchInterval:
          queryIdentifier === "get_gamestate"
            ? gameStateRefetchInterval
            : defaultRefetchInterval,
        ...query,
        enabled: canQueryGameServer && routeAllowsQuery,
      });
    }),
  });

  const statusQuery = queryResults[0];
  const gameStateQuery = queryResults[1];
  const serversQuery = queryResults[2];
  const ingameModsQuery = queryResults[3];
  const crconModsQuery = queryResults[4];

  useEffect(() => {
    const gameServerHealth = applyDemoHealth(
      createConnectionHealth(statusQuery, {
        enabled: canQueryGameServer,
      }),
      "gameServer"
    );
    const gameStateHealth = applyDemoHealth(
      createConnectionHealth(gameStateQuery, {
        enabled: canQueryGameServer,
      }),
      "gameState"
    );

    useGlobalStore.setState({
      serverState: crconQuery.data ?? null,
      status: statusQuery?.data ?? null,
      gameState: gameStateQuery?.data ?? null,
      servers: serversQuery?.data ?? [],
      onlineIngameMods: pollModeratorPresence
        ? (ingameModsQuery?.data ?? [])
        : [],
      onlineCrconMods: pollModeratorPresence ? (crconModsQuery?.data ?? []) : [],
      onlinePlayers: canQueryGameServer && pollLiveRoster
        ? useGlobalStore.getState().onlinePlayers
        : [],
      connectionHealth: {
        crcon: crconHealth,
        gameServer: gameServerHealth,
        gameState: gameStateHealth,
        gameData: createAggregateConnectionHealth(
          gameServerHealth,
          gameStateHealth
        ),
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
    pollLiveRoster,
    pollModeratorPresence,
  ]);

  return null;
};
