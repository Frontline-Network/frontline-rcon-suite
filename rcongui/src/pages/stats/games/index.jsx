import { useReactTable } from "@tanstack/react-table";
import { GameListTable } from "./game-list-table";
import { createGameListColumns } from "./game-list-columns";
import { cmd } from "@/utils/fetchUtils";
import { useLoaderData, useSearchParams } from "react-router-dom";
import {
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
} from "@tanstack/react-table";
import { gameQueryOptions } from "@/queries/game-query";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useMemo } from "react";
import PageHeader from "@/components/shared/PageHeader";
import { demoGames, isFakeMode } from "@/mirage/demo-data";

export const loader = async () => {
  if (isFakeMode()) return { maps: demoGames, total: demoGames.length };
  return await cmd.GET_COMPLETED_GAMES();
};

export const GamesList = () => {
  const { t } = useTranslation();
  const columns = useMemo(() => createGameListColumns(t), [t]);
  const data = useLoaderData();

  const [searchParams] = useSearchParams();
  const page = Number(searchParams.get("page") ?? 1);
  const pageSize = Number(searchParams.get("page_size") ?? 50);
  const maxPages = Math.ceil(data.total / pageSize);

  const { data: games, isLoading } = useQuery({
    ...gameQueryOptions.list(page, pageSize),
    initialData: data,
  });

  const table = useReactTable({
    columns: columns,
    data: games?.maps ?? [],
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    filterFns: {
      mapFilter: (row, id, filterValue) => {
        return row.original.map.pretty_name
          .toLowerCase()
          .includes(filterValue.toLowerCase());
      },
    },
  });

  return (
    <div>
      <PageHeader
        eyebrow={t("stats.games.eyebrow")}
        title={t("stats.games.title")}
        subtitle={t("stats.games.subtitle")}
      />
      <GameListTable table={table} page={page} maxPages={maxPages} />
    </div>
  );
};

const GamesPage = () => {
  return <GamesList />;
};

export default GamesPage;
