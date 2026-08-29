import { GameListTable } from "./game-list-table";
import { cmd } from "@/utils/fetchUtils";
import { useLoaderData, useSearchParams } from "react-router-dom";
import { gameQueryOptions } from "@/queries/game-query";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useEffect } from "react";
import PageHeader from "@/components/shared/PageHeader";
import { demoGames, isFakeMode } from "@/mirage/demo-data";

const parsePositiveInteger = (value, fallback) => {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
};

export const loader = async ({ request }) => {
  const url = new URL(request.url);
  const page = parsePositiveInteger(url.searchParams.get("page"), 1);
  const pageSize = Math.min(
    parsePositiveInteger(url.searchParams.get("page_size"), 50),
    100
  );

  if (isFakeMode()) {
    const start = (page - 1) * pageSize;
    return {
      maps: demoGames.slice(start, start + pageSize),
      page,
      page_size: pageSize,
      total: demoGames.length,
    };
  }

  return await cmd.GET_COMPLETED_GAMES({
    params: { page, limit: pageSize },
  });
};

export const GamesList = () => {
  const { t } = useTranslation();
  const data = useLoaderData();

  const [searchParams, setSearchParams] = useSearchParams();
  const page = parsePositiveInteger(searchParams.get("page"), 1);
  const pageSize = Math.min(
    parsePositiveInteger(searchParams.get("page_size"), 50),
    100
  );

  const gamesQuery = useQuery({
    ...gameQueryOptions.list(page, pageSize),
    initialData: data,
    placeholderData: (previousData) => previousData,
  });

  const games = gamesQuery.data ?? data;
  const total = Number(games?.total ?? 0);
  const currentPage = parsePositiveInteger(games?.page, page);
  const currentPageSize = parsePositiveInteger(games?.page_size, pageSize);
  const maxPages = Math.max(1, Math.ceil(total / currentPageSize));

  useEffect(() => {
    if (total > 0 && page > maxPages) {
      const next = new URLSearchParams(searchParams);
      next.set("page", String(maxPages));
      setSearchParams(next, { replace: true });
    }
  }, [maxPages, page, searchParams, setSearchParams, total]);

  return (
    <div>
      <PageHeader
        eyebrow={t("stats.games.eyebrow")}
        title={t("stats.games.title")}
        subtitle={t("stats.games.subtitle")}
      />
      <GameListTable
        games={games?.maps ?? []}
        total={total}
        page={currentPage}
        pageSize={currentPageSize}
        maxPages={maxPages}
        isLoading={gamesQuery.isLoading}
        isFetching={gamesQuery.isFetching}
        isError={gamesQuery.isError}
        error={gamesQuery.error}
        onRetry={gamesQuery.refetch}
      />
    </div>
  );
};

const GamesPage = () => {
  return <GamesList />;
};

export default GamesPage;
