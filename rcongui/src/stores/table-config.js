import { create } from "zustand";
import { persist } from "zustand/middleware";
import siteConfig from "@/config/siteConfig";
import { safeBrowserStorage } from "./safe-browser-storage";

const prefix = siteConfig.appName + ".";
const withPrefix = (key) => prefix + key;

// Player-table presentation is account-owned via useLiveViewPreferences.
// Do not import the old shared-browser players-table storage into an account.

// Logs table store
export const useLogsTableStore = create(
  persist(
    (set) => ({
      columnVisibility: {
        player_name_2: false,
        player_name_1: false,
        message: false,
        short_message: false,
        full_message: false,
        team: false,
      },
      filters: {
        actions: {
          enabled: false,
          selected: [],
        },
      },
      actions: [],
      highlighted: false,
      fontSize: "small",
      density: "dense",
      pagination: {
        pageIndex: 0,
        pageSize: 100,
      },

      setColumnVisibility: (columnId, isVisible) =>
        set((state) => {
          const columnVisibility = { ...state.columnVisibility };
          columnVisibility[columnId] === false
            ? delete columnVisibility[columnId]
            : (columnVisibility[columnId] = isVisible);
          return { ...state, columnVisibility };
        }),
      setFilters: (filters) => set({ filters }),
      setActions: (actions) => set({ actions }),
      setHighlighted: (highlighted) => set({ highlighted }),
      setConfig: (config) => set(config),
      setPagination: (pagination) => set({ pagination }),
    }),
    {
      name: withPrefix("logs-table"),
      storage: safeBrowserStorage,
    }
  )
);

// Logs search params store
export const useLogsSearchStore = create(
  persist(
    (set) => ({
      limit: 500,
      actions: [],
      players: [],
      inclusive_filter: true,
      enabled: true,
      setEnabled: (enabled) => set({ enabled }),
      setLimit: (limit) => set({ limit }),
      setActions: (actions) => set({ actions }),
      setPlayers: (players) => set({ players }),
      setInclusiveFilter: (inclusive) => set({ inclusive_filter: inclusive }),
      setSearchParams: (params) => set(params),
    }),
    {
      name: withPrefix("logs-search"),
      storage: safeBrowserStorage,
    }
  )
);

// Game list table store
export const useGameListTableStore = create(
  persist(
    (set) => ({
      columnVisibility: {},
      fontSize: "small",
      density: "dense",

      setColumnVisibility: (columnId, isVisible) =>
        set((state) => {
          const columnVisibility = { ...state.columnVisibility };
          columnVisibility[columnId] === false
            ? delete columnVisibility[columnId]
            : (columnVisibility[columnId] = isVisible);
          return { ...state, columnVisibility };
        }),
      setConfig: (config) => set(config),
    }),
    {
      name: withPrefix("game-list-table"),
      storage: safeBrowserStorage,
    }
  )
);

// Game details table store
export const useGameDetailsTableStore = create(
  persist(
    (set) => ({
      columnVisibility: {},
      fontSize: "small",
      density: "dense",

      setColumnVisibility: (columnId, isVisible) =>
        set((state) => {
          const columnVisibility = { ...state.columnVisibility };
          columnVisibility[columnId] === false
            ? delete columnVisibility[columnId]
            : (columnVisibility[columnId] = isVisible);
          return { ...state, columnVisibility };
        }),
      setConfig: (config) => set(config),
    }),
    {
      name: withPrefix("game-details-table"),
      storage: safeBrowserStorage,
    }
  )
);

// Live sessions table store
export const useLiveSessionsTableStore = create(
  persist(
    (set) => ({
      columnVisibility: {},
      fontSize: "small",
      density: "dense",

      setColumnVisibility: (columnId, isVisible) =>
        set((state) => {
          const columnVisibility = { ...state.columnVisibility };
          columnVisibility[columnId] === false
            ? delete columnVisibility[columnId]
            : (columnVisibility[columnId] = isVisible);
          return { ...state, columnVisibility };
        }),
      setConfig: (config) => set(config),
    }),
    {
      name: withPrefix("live-sessions-table"),
      storage: safeBrowserStorage,
    }
  )
);
