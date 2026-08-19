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
      let result;
      try {
        if (isFakeMode() && getDemoConnectionMode() === "gameserver_offline") {
          throw new Error("Demo game server is offline");
        }
        result = isFakeMode()
          ? getDemoServerStatus()
          : await cmd.GET_GAME_SERVER_STATUS()
        useGlobalStore.setState((state) => ({ status: result }));
      } catch (error) {
        useGlobalStore.setState((state) => ({ status: null }));
        return null;
      }
      return result
    },
    retry: 1,
  }),
  queryOptions({
    queryKey: [{ queryIdentifier: "get_gamestate" }],
    queryFn: isFakeMode() ? () => Promise.resolve(demoGameState) : cmd.GET_GAME_STATE,
    select: (data) => {
      useGlobalStore.setState((state) => ({ gameState: data }));
      return data;
    },
  }),
  queryOptions({
    queryKey: [{ queryIdentifier: "get_server_list" }],
    queryFn: isFakeMode() ? () => Promise.resolve(getDemoServerList()) : cmd.GET_GAME_SERVER_LIST,
    select: (data) => {
      useGlobalStore.setState((state) => ({ servers: data }));
      return data;
    },
  }),
  queryOptions({
    queryKey: [{ queryIdentifier: "get_ingame_mods" }],
    queryFn: isFakeMode() ? () => Promise.resolve([]) : cmd.GET_INGAME_MODS,
    select: (data) => {
      useGlobalStore.setState((state) => ({ onlineIngameMods: data }));
      return data;
    },
  }),
  queryOptions({
    queryKey: [{ queryIdentifier: "get_online_mods" }],
    queryFn: isFakeMode() ? () => Promise.resolve([]) : cmd.GET_CRCON_MODS,
    select: (data) => {
      useGlobalStore.setState((state) => ({ onlineCrconMods: data }));
      return data;
    },
  }),
  teamsLiveQueryOptions,
];

export const GlobalState = () => {
  const { data, isSuccess: isCrconConnected } = useQuery({
    queryKey: [{ queryIdentifier: "get_connection_info" }],
    queryFn: isFakeMode()
      ? () => {
          if (getDemoConnectionMode() === "crcon_offline") {
            return Promise.reject(new Error("Demo CRCON is offline"));
          }
          return Promise.resolve(getDemoServerConnection());
        }
      : cmd.GET_CRCON_SERVER_CONNECTION,
    refetchInterval,
    retry: isFakeMode() ? 0 : 1,
  });

  useEffect(() => {
    if (isCrconConnected) {
      useGlobalStore.setState({ serverState: data });
    } else {
      useGlobalStore.setState({
        serverState: null,
        status: null,
        gameState: null,
        onlineIngameMods: [],
        onlineCrconMods: [],
        onlinePlayers: [],
      });
    }
  }, [data, isCrconConnected]);

  useQueries({
    queries: globalQueries.map((query) => queryOptions({
      staleTime,
      refetchInterval,
      enabled: isCrconConnected,
      ...query,
    })),
  });

  return null;
};
