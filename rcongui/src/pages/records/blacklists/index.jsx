import {
  Button,
  LinearProgress,
} from "@mui/material";
import Grid from "@mui/material/Grid2";
import BlacklistRecordsSearch from "@/components/Blacklist/BlacklistRecordsSearch";
import {
  addPlayerToBlacklist,
  get,
  getBlacklists,
  handle_http_errors,
  showResponse,
} from "@/utils/fetchUtils";
import Pagination from '@mui/material/Pagination';
import BlacklistRecordGrid from "@/components/Blacklist/BlacklistRecordGrid";
import { List, fromJS } from "immutable";
import { BlacklistRecordCreateButton } from "@/components/Blacklist/BlacklistRecordCreateDialog";
import { Skeleton } from '@mui/material';
import { Link } from "react-router-dom";
import {useEffect, useState} from "react";
import { useTranslation } from "react-i18next";
import PageHeader from "@/components/shared/PageHeader";
import { demoBlacklists, demoBlacklistRecords, isFakeMode } from "@/mirage/demo-data";

async function getBlacklistRecords(searchParams) {
  let path = "get_blacklist_records?" + new URLSearchParams(
    Object.entries(searchParams)
      .filter(([_, v]) => v || v === 0)
  );
  const response = await get(path)
  return showResponse(response, "get_blacklist_records")
}

const MyPagination = ({ pageSize, total, page, setPage, t }) => (
  <Pagination
    count={Math.ceil(total / pageSize)}
    page={page}
    onChange={(e, val) => setPage(val)}
    variant="outlined"
    color="standard"
    showFirstButton
    showLastButton
    getItemAriaLabel={(type, itemPage) =>
      type === "page"
        ? t("common.pagination.pageAria", { page: itemPage })
        : t(`common.pagination.${type}`)
    }
  />
);

const BlacklistRecords = () => {
  const { t } = useTranslation();
  // inital state, first render
  const [isLoading, setIsLoading] = useState(true);
  // when fetching loading records
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
    page_size: 50,
  });

  useEffect(() => {
    if (!blacklists.length) {
      loadBlacklists();
    }
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
        setRecords(fromJS(demoBlacklistRecords));
        setTotalRecords(demoBlacklistRecords.length);
        setIsFetching(false);
        setIsLoading(false);
        return;
      }
      const data = await getBlacklistRecords({ ...searchQuery, page });
      const records = data.result;
      if (records) {
        setRecords(fromJS(records.records));
        setTotalRecords(records.total);
      }
      setIsFetching(false);
      // delay UI, this can be removed along with skeletons
      await new Promise((res) => setTimeout(res, 500));
      setIsLoading(false);
    } catch (error) {
      handle_http_errors(error);
    }
  }

  async function createRecord(recordDetails) {
    if (isFakeMode()) {
      const selectedList = demoBlacklists.find((item) => item.id === recordDetails.blacklistId) || demoBlacklists[0];
      const demoRecord = {
        id: Date.now(),
        blacklist: selectedList,
        player: { player_id: recordDetails.playerId, names: [{ name: recordDetails.playerId }], steaminfo: null },
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

  // If you don't like the loading skeletons, just return `null`
  if (isLoading) {
    return (
      <>
      <PageHeader
        eyebrow={t("records.blacklists.eyebrow")}
        title={t("records.blacklists.title")}
        subtitle={t("records.blacklists.subtitle")}
      />
      <Grid container spacing={4} justifyContent="center">
        <Grid
          size={{
            xl: 6,
            xs: 12
          }}>
          <Skeleton variant="rectangular" height={140} />
        </Grid>
        <Grid
          container
          justifyContent="center"
          spacing={2}
          size={{
            xl: 3,
            xs: 12
          }}>
          <Grid size={{
            xl: 12
          }}>
            <Skeleton
              variant="rectangular"
              width={200}
              height={42}
              style={{ margin: "0 auto", borderRadius: 5 }}
            />
          </Grid>
          <Grid size={{
            xl: 12
          }}>
            <Skeleton
              variant="rectangular"
              width={155}
              height={42}
              style={{ margin: "0 auto", borderRadius: 5 }}
            />
          </Grid>
        </Grid>
        <Grid size={12}>
          <Skeleton
            variant="rectangular"
            width={360}
            height={32}
            style={{ margin: "0 auto" }}
          />
        </Grid>
        <Grid size={12}>
          <Skeleton variant="rectangular" height={140} />
        </Grid>
        <Grid size={12}>
          <Skeleton
            variant="rectangular"
            width={360}
            height={32}
            style={{ margin: "0 auto" }}
          />
        </Grid>
      </Grid>
      </>
    );
  }

  return (
    <>
    <PageHeader
      eyebrow={t("records.blacklists.eyebrow")}
      title={t("records.blacklists.title")}
      subtitle={t("records.blacklists.subtitle")}
    />
    <Grid container spacing={3} justifyContent="center" sx={{ mt: 1 }}>
      <Grid
        size={{
          xl: 6,
          xs: 12
        }}>
        <BlacklistRecordsSearch
          blacklists={blacklists}
          onSearch={setSearchQuery}
          disabled={isLoading || isFetching}
        />
      </Grid>
      <Grid
        size={{
          xl: 3,
          xs: 12
        }}>
        <Grid
          container
          spacing={3}
          alignContent="center"
          alignItems="center"
          justifyContent="center"
          style={{ paddingTop: 6 }}
        >
          <Grid size={{
            xl: 12
          }}>
            <BlacklistRecordCreateButton
              blacklists={blacklists}
              onSubmit={createRecord}
            >
              {t("records.blacklists.createRecord")}
            </BlacklistRecordCreateButton>
          </Grid>
          <Grid size={{
            xl: 12
          }}>
            <Button
              component={Link}
              to={"manage"}
              variant="contained"
              color="primary"
              size="large"
            >
              {t("records.blacklists.manageLists")}
            </Button>
          </Grid>
        </Grid>
      </Grid>
      <Grid size={12}>
        <MyPagination
          pageSize={searchQuery.page_size}
          page={page}
          setPage={setPage}
          total={totalRecords}
          t={t}
        />
      </Grid>
      <Grid size={12}>
        {isFetching ? <LinearProgress color="secondary" /> : ""}
        <BlacklistRecordGrid
          blacklists={blacklists}
          records={records}
          onRefresh={loadRecords}
        />
      </Grid>
      <Grid size={12}>
        <MyPagination
          pageSize={searchQuery.page_size}
          page={page}
          setPage={setPage}
          total={totalRecords}
          t={t}
        />
      </Grid>
    </Grid>
    </>
  );
}

export default BlacklistRecords;
