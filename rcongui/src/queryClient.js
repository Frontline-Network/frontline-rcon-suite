import { QueryClient } from "@tanstack/react-query";

// Create a new QueryClient instance with default options
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      gcTime: 1000 * 60 * 30, // v5: inactive queries; live logs override this.
      // Hidden admin tabs must not keep polling every connected CRCON.
      // Stale queries refresh normally when the operator returns to the tab.
      refetchIntervalInBackground: false,
    },
  },
});
