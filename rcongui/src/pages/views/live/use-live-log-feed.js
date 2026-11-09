import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cmd } from "@/utils/fetchUtils";
import {
  LIVE_LOG_GC_TIME,
  LIVE_LOG_PAGE_SIZE,
  mergeLogPage,
} from "./live-log-feed.mjs";

export function useLiveLogFeed(search) {
  const client = useQueryClient();
  const [paused, setPaused] = useState(false);
  const [scrollReset, setScrollReset] = useState(0);
  const limit = Math.min(100_000, Math.max(1, Number(search.limit) || 500));
  const params = useMemo(
    () => ({
      cursor_mode: true,
      end: Math.min(limit, LIVE_LOG_PAGE_SIZE),
      filter_action: search.enabled ? search.actions : [],
      filter_player: search.enabled ? search.players : [],
      inclusive_filter: search.inclusive_filter,
    }),
    [
      limit,
      search.enabled,
      search.actions,
      search.players,
      search.inclusive_filter,
    ]
  );
  const queryKey = useMemo(
    () => ["logs", "live", "cursor-v1", limit, params],
    [limit, params]
  );
  const filterKey = JSON.stringify(queryKey);
  useEffect(() => {
    setPaused(false);
  }, [filterKey]);
  useEffect(() => {
    if (paused) client.cancelQueries({ queryKey, exact: true });
  }, [paused, client, queryKey]);

  const query = useQuery({
    queryKey,
    queryFn: async ({ signal }) => {
      const current = client.getQueryData(queryKey);
      const response = await cmd.GET_LIVE_LOGS({
        payload: { ...params, after: current?.newest ?? undefined },
        signal,
        throwRouteError: false,
      });
      return mergeLogPage(current, response.result, "newer", limit);
    },
    enabled: !paused,
    refetchInterval: 15_000,
    retry: 1,
    gcTime: LIVE_LOG_GC_TIME,
  });
  const older = useMutation({
    mutationFn: async ({ key, request, maximum }) => {
      await client.cancelQueries({ queryKey: key, exact: true });
      const current = client.getQueryData(key);
      if (
        !current?.oldest ||
        !current.has_older ||
        current.logs.length >= maximum
      )
        return null;
      const response = await cmd.GET_LIVE_LOGS({
        payload: {
          ...request,
          end: Math.min(request.end, maximum - current.logs.length),
          before: current.oldest,
        },
        throwRouteError: false,
      });
      return response.result;
    },
    onSuccess: (page, { key, maximum }) => {
      if (page)
        client.setQueryData(key, (current) =>
          mergeLogPage(current, page, "older", maximum)
        );
    },
    gcTime: LIVE_LOG_GC_TIME,
  });
  const resetOlder = older.reset;
  useEffect(() => {
    resetOlder();
  }, [filterKey, resetOlder]);
  return {
    ...query,
    paused,
    filterKey,
    scrollReset,
    pause: () => setPaused(true),
    resume: () => {
      setScrollReset((value) => value + 1);
      setPaused(false);
    },
    loadOlder: () => {
      setPaused(true);
      older.mutate({ key: queryKey, request: params, maximum: limit });
    },
    isLoadingOlder: older.isPending,
    error: query.error || older.error,
    retry: () => {
      if (older.isError && older.variables) older.mutate(older.variables);
      else query.refetch();
    },
    canLoadOlder:
      Boolean(query.data?.has_older) && query.data.logs.length < limit,
    atLimit: (query.data?.logs.length ?? 0) >= limit,
    clearNotice: () =>
      client.setQueryData(queryKey, (current) =>
        current ? { ...current, reset: null } : current
      ),
  };
}
