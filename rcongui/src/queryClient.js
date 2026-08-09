import { QueryClient } from '@tanstack/react-query';

// Create a new QueryClient instance with default options
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      cacheTime: 1000 * 60 * 30, // 30 minutes
      // Polling should only keep the currently visible admin tab fresh. React
      // Query refetches stale data when the user returns to the tab.
      refetchIntervalInBackground: false,
    },
  },
});
