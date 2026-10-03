import { useQuery } from "@tanstack/react-query";
import { create } from "zustand";
import { useAuth } from "./useAuth";
import { cmd } from "@/utils/fetchUtils";

const useReadUpdates = create((set) => ({
  values: {},
  remember: (key, tags) =>
    set((state) => ({ values: { ...state.values, [key]: tags } })),
}));

function readTags(key) {
  try {
    const value = JSON.parse(localStorage.getItem(key));
    return Array.isArray(value)
      ? value.filter((tag) => typeof tag === "string")
      : [];
  } catch {
    return [];
  }
}

export function useUpdateChannel({ poll = false } = {}) {
  const { user } = useAuth();
  const query = useQuery({
    queryKey: [
      "installed-update-channel",
      process.env.REACT_APP_API_URL,
      process.env.REACT_APP_VERSION,
      user?.username,
    ],
    queryFn: () =>
      cmd.GET_UPDATE_CHANNEL({
        params: { frontend_version: process.env.REACT_APP_VERSION },
        throwRouteError: false,
      }),
    staleTime: 60_000,
    gcTime: 0,
    refetchInterval: poll ? 60_000 : false,
    refetchIntervalInBackground: false,
    retry: false,
  });
  // No persistent release payload and no fallback to the old unfiltered cache.
  // A failed/unverified response must never announce an update.
  const data = query.isError ? null : query.data;
  const key = `crcon.updates.read:${window.location.origin}:${
    data?.reader_id || "pending"
  }`;
  const remembered = useReadUpdates((state) => state.values[key]);
  const remember = useReadUpdates((state) => state.remember);
  const read = remembered || readTags(key);
  const releases =
    data?.status === "ready" && Array.isArray(data.releases)
      ? data.releases
      : [];
  const unreadCount = releases.some(
    (release) => release.current && !read.includes(release.tag_name)
  )
    ? 1
    : 0;
  const markAsRead = () => {
    if (!data?.reader_id) return;
    const tags = [
      ...new Set([...read, ...releases.map((release) => release.tag_name)]),
    ].slice(-100);
    remember(key, tags);
    try {
      localStorage.setItem(key, JSON.stringify(tags));
    } catch {
      /* Memory fallback. */
    }
  };
  return {
    ...query,
    data,
    releases,
    unreadCount,
    markAsRead,
    lastUpdate: data?.checked_at,
    forceUpdate: query.refetch,
  };
}
