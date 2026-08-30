import { create } from "zustand";
import { persist } from "zustand/middleware";
import siteConfig from "@/config/siteConfig";
import { DEFAULT_APPEARANCE, normalizeAppearance } from "@/themes/appearance";

const prefix = siteConfig.appName + ".";
const withPrefix = (key) => prefix + key;

export const useAppStore = create(
  persist(
    (set, get) => ({
      appearance: DEFAULT_APPEARANCE,
      appearancePreview: null,
      appearanceByUser: {},
      activeAppearanceUser: null,
      selectAppearanceUser: (userKey) =>
        set((state) => {
          const normalizedKey = String(userKey || "").trim();
          if (!normalizedKey || normalizedKey === state.activeAppearanceUser) {
            return state;
          }
          return {
            activeAppearanceUser: normalizedKey,
            appearance: normalizeAppearance(
              state.appearanceByUser?.[normalizedKey] || DEFAULT_APPEARANCE
            ),
            appearancePreview: null,
          };
        }),
      hydrateAppearance: (value, userKey) =>
        set((state) => {
          const normalized = normalizeAppearance(value);
          const normalizedKey = String(
            userKey || state.activeAppearanceUser || ""
          ).trim();
          return {
            appearance: normalized,
            appearancePreview: null,
            ...(normalizedKey
              ? {
                  activeAppearanceUser: normalizedKey,
                  appearanceByUser: {
                    ...state.appearanceByUser,
                    [normalizedKey]: normalized,
                  },
                }
              : {}),
          };
        }),
      setAppearance: (value) =>
        set((state) => {
          const normalized = normalizeAppearance(value);
          const userKey = state.activeAppearanceUser;
          return {
            appearance: normalized,
            appearancePreview: null,
            appearanceByUser: userKey
              ? { ...state.appearanceByUser, [userKey]: normalized }
              : state.appearanceByUser,
          };
        }),
      setAppearancePreview: (value) =>
        set({ appearancePreview: value ? normalizeAppearance(value) : null }),
      clearAppearancePreview: () => set({ appearancePreview: null }),
      widthMode: "xl",
      toggleWidthMode: () =>
        set({ widthMode: get().widthMode === "xl" ? false : "xl" }),
      openDrawer: true,
      setDrawerOpen: (open) => set({ openDrawer: Boolean(open) }),
      toggleDrawer: () => set({ openDrawer: !get().openDrawer }),
      // Persist which navigation groups are expanded.
      groupOpenState: {},
      toggleMenuGroupOpen: (groupName) =>
        set((state) => ({
          groupOpenState: {
            ...state.groupOpenState,
            [groupName]: !state.groupOpenState?.[groupName],
          },
        })),
    }),
    {
      name: withPrefix("app"),
      version: 2,
      migrate: (persistedState, version) => {
        if (version < 2) {
          const legacyPreset = {
            default: "frontline-gold",
            original: "frontline-gold",
            github: "tactical-blue",
            lime: "signal-green",
            highContrast: "neutral",
          }[persistedState?.colorScheme];
          return {
            ...persistedState,
            appearance: normalizeAppearance({
              ...DEFAULT_APPEARANCE,
              preset: legacyPreset || DEFAULT_APPEARANCE.preset,
            }),
            appearanceByUser: {},
            activeAppearanceUser: null,
          };
        }
        return persistedState;
      },
      partialize: (state) => ({
        appearance: state.appearance,
        appearanceByUser: state.appearanceByUser,
        activeAppearanceUser: state.activeAppearanceUser,
        widthMode: state.widthMode,
        openDrawer: state.openDrawer,
        groupOpenState: state.groupOpenState,
      }),
    }
  )
);
