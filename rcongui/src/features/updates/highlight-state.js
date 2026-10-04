import { create } from "zustand";

// UI intent only; acknowledgement remains in the signed-in user's backend record.
export const useHighlightUI = create((set) => ({
  requested: false,
  requestOpen: () => set({ requested: true }),
  clearRequest: () => set({ requested: false }),
}));
