import { QueryClient } from "@tanstack/react-query";

// Create a new QueryClient instance with default options
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      cacheTime: 1000 * 60 * 30, // 30 minutes
      // Hidden admin tabs must not keep polling every connected CRCON.
      // Stale queries refresh normally when the operator returns to the tab.
      refetchIntervalInBackground: false,
    },
  },
});
