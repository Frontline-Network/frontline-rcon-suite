import { focusManager, QueryClient } from '@tanstack/react-query'
import { STALE_TIME } from './constants'

if (typeof document !== 'undefined') {
  focusManager.setEventListener((setFocused) => {
    const syncFocusWithVisibility = () => {
      setFocused(document.visibilityState === 'visible')
    }

    document.addEventListener(
      'visibilitychange',
      syncFocusWithVisibility,
      false,
    )
    syncFocusWithVisibility()

    return () => {
      document.removeEventListener(
        'visibilitychange',
        syncFocusWithVisibility,
      )
    }
  })
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: STALE_TIME,
      refetchIntervalInBackground: false,
    },
  },
})
