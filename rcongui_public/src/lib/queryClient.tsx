import {
  focusManager,
  onlineManager,
  QueryClient,
} from '@tanstack/react-query'
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

  onlineManager.setEventListener((setOnline) => {
    const syncOnlineWithVisibility = () => {
      setOnline(
        document.visibilityState === 'visible' && navigator.onLine !== false,
      )
    }

    window.addEventListener('online', syncOnlineWithVisibility, false)
    window.addEventListener('offline', syncOnlineWithVisibility, false)
    document.addEventListener(
      'visibilitychange',
      syncOnlineWithVisibility,
      false,
    )
    syncOnlineWithVisibility()

    return () => {
      window.removeEventListener('online', syncOnlineWithVisibility)
      window.removeEventListener('offline', syncOnlineWithVisibility)
      document.removeEventListener(
        'visibilitychange',
        syncOnlineWithVisibility,
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
