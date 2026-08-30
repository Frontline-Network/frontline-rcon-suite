import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Box,
  Button,
  LinearProgress,
  Pagination,
  Skeleton,
  Stack,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import ListAltIcon from "@mui/icons-material/ListAlt";
import { List, fromJS } from "immutable";
import { useTranslation } from "react-i18next";
import BlacklistRecordsSearch from "@/components/Blacklist/BlacklistRecordsSearch";
import BlacklistRecordGrid from "@/components/Blacklist/BlacklistRecordGrid";
import { BlacklistRecordCreateButton } from "@/components/Blacklist/BlacklistRecordCreateDialog";
import {
  addPlayerToBlacklist,
  get,
  getBlacklists,
  handle_http_errors,
  showResponse,
} from "@/utils/fetchUtils";
import PageHeader from "@/components/shared/PageHeader";
import {
  demoBlacklists,
  demoBlacklistRecords,
  isFakeMode,
} from "@/mirage/demo-data";

async function getBlacklistRecords(searchParams) {
  const path =
    "get_blacklist_records?" +
    new URLSearchParams(
      Object.entries(searchParams).filter(([, value]) => value || value === 0)
    );
  const response = await get(path);
  return showResponse(response, "get_blacklist_records");
}

const BlacklistRecords = () => {
  const { t } = useTranslation();
  const [isLoading, setIsLoading] = useState(true);
  const [isFetching, setIsFetching] = useState(false);
  const [blacklists, setBlacklists] = useState([]);
  const [records, setRecords] = useState(List());
  const [totalRecords, setTotalRecords] = useState(0);
  const [page, setPage] = useState(1);
  const [searchQuery, setSearchQuery] = useState({
    player_id: undefined,
    reason: undefined,
    blacklist_id: undefined,
    exclude_expired: false,
    expired_only: false,
    page_size: 50,
  });

  useEffect(() => {
    if (!blacklists.length) loadBlacklists();
    loadRecords();
  }, [searchQuery, page]);

  async function loadBlacklists() {
    if (isFakeMode()) {
      setBlacklists(demoBlacklists);
      return;
    }
    setBlacklists(await getBlacklists());
  }

  async function loadRecords() {
    setIsFetching(true);
    try {
      if (isFakeMode()) {
        const filtered = demoBlacklistRecords.filter((record) => {
          const matchesPlayer =
            !searchQuery.player_id ||
            record.player.player_id === searchQuery.player_id;
          const haystack = `${record.player.names
            .map((name) => name.name)
            .join(" ")} ${record.formatted_reason}`.toLowerCase();
          const matchesReason =
            !searchQuery.reason ||
            haystack.includes(searchQuery.reason.toLowerCase());
          const matchesList =
            searchQuery.blacklist_id === undefined ||
            searchQuery.blacklist_id === null ||
            record.blacklist.id === Number(searchQuery.blacklist_id);
          const matchesStatus = searchQuery.expired_only
            ? !record.is_active
            : searchQuery.exclude_expired
            ? record.is_active
            : true;
          return matchesPlayer && matchesReason && matchesList && matchesStatus;
        });
        setRecords(fromJS(filtered));
        setTotalRecords(filtered.length);
        return;
      }

      const data = await getBlacklistRecords({ ...searchQuery, page });
      const result = data.result;
      if (result) {
        setRecords(fromJS(result.records));
        setTotalRecords(result.total);
      }
    } catch (error) {
      handle_http_errors(error);
    } finally {
      setIsFetching(false);
      setIsLoading(false);
    }
  }

  async function createRecord(recordDetails) {
    if (isFakeMode()) {
      const selectedList =
        demoBlacklists.find((item) => item.id === recordDetails.blacklistId) ||
        demoBlacklists[0];
      const demoRecord = {
        id: Date.now(),
        blacklist: selectedList,
        player: {
          player_id: recordDetails.playerId,
          names: [{ name: recordDetails.playerId }],
          steaminfo: null,
        },
        reason: recordDetails.reason,
        formatted_reason: recordDetails.reason,
        created_at: new Date().toISOString(),
        expires_at: recordDetails.expiresAt?.toISOString?.() || null,
        is_active: true,
        admin_name: "Frontline Admin",
      };
      setRecords((current) => current.unshift(fromJS(demoRecord)));
      setTotalRecords((current) => current + 1);
      return;
    }
    await addPlayerToBlacklist(recordDetails);
    loadRecords();
  }

  const handleSearch = (query) => {
    setPage(1);
    setSearchQuery(query);
  };

  const pageCount = Math.max(
    1,
    Math.ceil(totalRecords / searchQuery.page_size)
  );
  const pageStart = totalRecords ? (page - 1) * searchQuery.page_size + 1 : 0;
  const pageEnd = Math.min(page * searchQuery.page_size, totalRecords);

  const headerActions = (
    <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
      <BlacklistRecordCreateButton
        blacklists={blacklists}
        onSubmit={createRecord}
      >
        <Stack direction="row" alignItems="center" gap={0.75}>
          <AddIcon fontSize="small" />
          <span>{t("records.blacklists.createRecordShort")}</span>
        </Stack>
      </BlacklistRecordCreateButton>
      <Button
        component={Link}
        to="manage"
        variant="outlined"
        color="inherit"
        startIcon={<ListAltIcon />}
        sx={{ borderRadius: 0, minHeight: 42 }}
      >
        {t("records.blacklists.manageLists")}
      </Button>
    </Stack>
  );

  return (
    <Stack spacing={1.25} sx={{ width: "100%", minWidth: 0, pb: 2 }}>
      <PageHeader
        eyebrow={t("records.blacklists.eyebrow")}
        title={t("records.blacklists.title")}
        subtitle={t("records.blacklists.subtitle")}
        actions={headerActions}
      />

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "minmax(0, 1fr)",
            lg: "270px minmax(0, 1fr)",
          },
          gap: 1.5,
          alignItems: "start",
          minWidth: 0,
        }}
      >
        <BlacklistRecordsSearch
          blacklists={blacklists}
          onSearch={handleSearch}
          disabled={isLoading || isFetching}
          totalRecords={totalRecords}
        />

        <Box sx={{ minWidth: 0 }}>
          {isFetching && !isLoading ? <LinearProgress sx={{ mb: 1 }} /> : null}
          {isLoading ? (
            <Stack gap={1}>
              <Skeleton variant="rectangular" height={58} />
              <Skeleton variant="rectangular" height={220} />
              <Skeleton variant="rectangular" height={58} />
            </Stack>
          ) : (
            <BlacklistRecordGrid
              blacklists={blacklists}
              records={records}
              onRefresh={loadRecords}
            />
          )}

          <Stack
            direction={{ xs: "column", sm: "row" }}
            alignItems={{ xs: "stretch", sm: "center" }}
            justifyContent="space-between"
            gap={1}
            sx={{ mt: 1.25, minHeight: 44 }}
          >
            <Typography variant="caption" color="text.secondary">
              {t("records.blacklists.range", {
                start: pageStart,
                end: pageEnd,
                total: totalRecords,
              })}
            </Typography>
            <Pagination
              count={pageCount}
              page={Math.min(page, pageCount)}
              onChange={(_, value) => setPage(value)}
              variant="outlined"
              color="standard"
              showFirstButton
              showLastButton
              disabled={isFetching}
              getItemAriaLabel={(type, itemPage) =>
                type === "page"
                  ? t("common.pagination.pageAria", { page: itemPage })
                  : t(`common.pagination.${type}`)
              }
              sx={{
                "& .MuiPaginationItem-root": { borderRadius: 0 },
                alignSelf: { xs: "flex-end", sm: "auto" },
              }}
            />
          </Stack>
        </Box>
      </Box>
    </Stack>
  );
};

export default BlacklistRecords;
