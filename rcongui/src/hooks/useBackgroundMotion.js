import { create } from "zustand";
import { useMediaQuery } from "@mui/material";

const STORAGE_KEY = "crcon.background-motion";
const readPreference = () => {
  try {
    return localStorage.getItem(STORAGE_KEY) !== "paused";
  } catch {
    return true;
  }
};

// A device preference: motion settings need no server request or account write.
const useMotionPreference = create((set) => ({
  enabled: readPreference(),
  toggle: () =>
    set((state) => {
      const enabled = !state.enabled;
      try {
        localStorage.setItem(STORAGE_KEY, enabled ? "enabled" : "paused");
      } catch {
        /* Keep the preference in memory when storage is unavailable. */
      }
      return { enabled };
    }),
}));

export function useBackgroundMotion() {
  const enabled = useMotionPreference((state) => state.enabled);
  const toggle = useMotionPreference((state) => state.toggle);
  const reduced = useMediaQuery("(prefers-reduced-motion: reduce)");
  return { enabled, reduced, playing: enabled && !reduced, toggle };
}
