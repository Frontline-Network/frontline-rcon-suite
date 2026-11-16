import { createJSONStorage } from 'zustand/middleware';
import { browserStorage } from '@/utils/browser-storage';

// A browser can expose localStorage yet reject individual reads or writes.
// Zustand keeps the current state in memory if persistence is unavailable.
export const safeBrowserStorage = createJSONStorage(() => browserStorage);
