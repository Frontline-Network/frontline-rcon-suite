import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { create } from "zustand";
import { useAuth } from "./useAuth";
import { cmd } from "@/utils/fetchUtils";
import { highlightReleaseForChannel } from "@/features/updates/highlight-release.mjs";

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
  const queryClient = useQueryClient();
  const queryKey = [
    "installed-update-channel",
    process.env.REACT_APP_API_URL,
    process.env.REACT_APP_VERSION,
    user?.username,
  ];
  const query = useQuery({
    queryKey,
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
  const currentRelease = releases.find((release) => release.current);
  const highlightRelease = highlightReleaseForChannel(data);
  const readerId = data?.reader_id;
  const releaseVersion = data?.highlight_state?.release_version;
  const channelStatus = data?.status;
  const setHighlightState = useCallback(
    async (action) => {
      if (!readerId || channelStatus !== "ready" || !releaseVersion) {
        throw new Error("Installed highlights unavailable");
      }
      const response = await cmd.SET_OWN_RELEASE_HIGHLIGHT_STATE({
        frontend_version: process.env.REACT_APP_VERSION,
        release_version: releaseVersion,
        action,
      });
      if (response?.failed || !response?.result)
        throw new Error("Highlight state not saved");
      queryClient.setQueryData(
        [
          "installed-update-channel",
          process.env.REACT_APP_API_URL,
          process.env.REACT_APP_VERSION,
          user?.username,
        ],
        (previous) =>
          previous?.reader_id === readerId &&
          previous?.highlight_state?.release_version === releaseVersion
            ? { ...previous, highlight_state: response.result }
            : previous
      );
      return response.result;
    },
    [readerId, channelStatus, releaseVersion, queryClient, user?.username]
  );
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
    currentRelease,
    highlightRelease,
    setHighlightState,
    unreadCount,
    markAsRead,
    lastUpdate: data?.checked_at,
    forceUpdate: query.refetch,
  };
}
