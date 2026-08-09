import { focusManager, QueryClient } from '@tanstack/react-query';

if (typeof document !== "undefined") {
  focusManager.setEventListener((setFocused) => {
    const syncFocusWithVisibility = () => {
      setFocused(document.visibilityState === "visible");
    };

    document.addEventListener(
      "visibilitychange",
      syncFocusWithVisibility,
      false,
    );
    syncFocusWithVisibility();

    return () => {
      document.removeEventListener(
        "visibilitychange",
        syncFocusWithVisibility,
      );
    };
  });
}

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
