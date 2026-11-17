import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  LinearProgress,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import DnsOutlinedIcon from "@mui/icons-material/DnsOutlined";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import SecurityOutlinedIcon from "@mui/icons-material/SecurityOutlined";
import SyncAltIcon from "@mui/icons-material/SyncAlt";
import BlacklistSyncReview from "./BlacklistSyncReview";
import BarricadeScanReview from "./BarricadeScanReview";
import {
  get,
  handle_http_errors,
  postData,
  showResponse,
} from "@/utils/fetchUtils";
import BlacklistListTile from "@/components/Blacklist/BlacklistListTile";
import BlacklistListCreateDialog, {
  BlacklistListCreateButton,
} from "@/components/Blacklist/BlacklistListCreateDialog";
import { Link } from "react-router-dom";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import PageHeader from "@/components/shared/PageHeader";
import {
  demoBlacklists,
  demoServerConnection,
  isFakeMode,
} from "@/mirage/demo-data";

const Metric = ({ label, value, icon }) => (
  <Paper
    variant="outlined"
    sx={{ borderRadius: 0, p: 1.25, minWidth: 0, bgcolor: "background.paper" }}
  >
    <Stack direction="row" spacing={1} alignItems="center">
      <Box sx={{ color: "primary.main", display: "inline-flex" }}>{icon}</Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography variant="caption" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="h6" sx={{ lineHeight: 1.2 }}>
          {value}
        </Typography>
      </Box>
    </Stack>
  </Paper>
);

const BlacklistLists = () => {
  const { t } = useTranslation();
  const [isLoading, setIsLoading] = useState(false);
  const [blacklists, setBlacklists] = useState([]);
  const [servers, setServers] = useState({});
  const [activeBlacklist, setActiveBlacklist] = useState(null);
  const [deleteCandidate, setDeleteCandidate] = useState(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editDialogInitialValues, setEditDialogInitialValues] = useState();

  const globalListCount = useMemo(
    () => blacklists.filter((blacklist) => blacklist.servers === null).length,
    [blacklists]
  );
  const immediateListCount = useMemo(
    () =>
      blacklists.filter((blacklist) => blacklist.sync === "ban_immediately")
        .length,
    [blacklists]
  );

  useEffect(() => {
    if (!blacklists.length) {
      setActiveBlacklist(null);
      return;
    }
    if (!blacklists.some((item) => item.id === activeBlacklist?.id)) {
      setActiveBlacklist(blacklists[0]);
    }
  }, [activeBlacklist?.id, blacklists]);

  function loadServers() {
    if (isFakeMode()) {
      setServers({
        [demoServerConnection.server_number]: demoServerConnection.name,
      });
      return Promise.resolve();
    }
    return Promise.all([
      get("get_connection_info")
        .then((response) =>
          showResponse(response, "get_connection_info", false)
        )
        .then((data) => {
          if (data.result) {
            setServers((previous) => ({
              ...previous,
              [data.result.server_number]: data.result.name,
            }));
          }
        })
        .catch(handle_http_errors),
      get("get_server_list")
        .then((response) => showResponse(response, "get_server_list", false))
        .then((data) => {
          if (data?.result) {
            setServers((previous) => ({
              ...previous,
              ...data.result.reduce((result, server) => {
                result[server.server_number] = server.name;
                return result;
              }, {}),
            }));
          }
        })
        .catch(handle_http_errors),
    ]);
  }

  function loadBlacklists() {
    if (isFakeMode()) {
      setBlacklists(demoBlacklists);
      return Promise.resolve();
    }
    return get("get_blacklists")
      .then((response) => showResponse(response, "get_blacklists", false))
      .then((data) => {
        if (data.result) setBlacklists(data.result);
      })
      .catch(handle_http_errors);
  }

  function onBlacklistCreate(data) {
    if (isFakeMode()) {
      const created = {
        id: Date.now(),
        name: data.name,
        servers: data.servers,
        sync: data.syncMethod,
      };
      setBlacklists((current) => [...current, created]);
      setActiveBlacklist(created);
      return;
    }
    postData(`${process.env.REACT_APP_API_URL}create_blacklist`, {
      name: data.name,
      servers: data.servers,
      sync: data.syncMethod,
    })
      .then((response) =>
        showResponse(response, `Blacklist ${data.name} was created`, true)
      )
      .catch(handle_http_errors)
      .then(loadBlacklists);
  }

  function onEditBlacklist(blacklist) {
    setEditDialogInitialValues({
      id: blacklist.id,
      name: blacklist.name,
      servers: blacklist.servers,
      syncMethod: blacklist.sync,
    });
    setEditDialogOpen(true);
  }

  function onEditDialogSubmit(data) {
    const blacklistId = editDialogInitialValues.id;
    if (isFakeMode()) {
      setBlacklists((current) =>
        current.map((item) =>
          item.id === blacklistId
            ? {
                ...item,
                name: data.name,
                servers: data.servers,
                sync: data.syncMethod,
              }
            : item
        )
      );
      return;
    }
    postData(`${process.env.REACT_APP_API_URL}edit_blacklist`, {
      blacklist_id: blacklistId,
      name: data.name,
      servers: data.servers,
      sync_method: data.syncMethod,
    })
      .then((response) =>
        showResponse(response, `Blacklist ${data.name} was edited`, true)
      )
      .catch(handle_http_errors)
      .then(loadBlacklists);
  }

  function deleteBlacklist(blacklist) {
    if (isFakeMode()) {
      setBlacklists((current) =>
        current.filter((item) => item.id !== blacklist.id)
      );
      return;
    }
    postData(`${process.env.REACT_APP_API_URL}delete_blacklist`, {
      blacklist_id: blacklist.id,
    })
      .then((response) =>
        showResponse(response, `Blacklist ${blacklist.name} was deleted`, true)
      )
      .catch(handle_http_errors)
      .then(loadBlacklists);
  }

  useEffect(() => {
    setIsLoading(true);
    loadServers()
      .then(loadBlacklists)
      .finally(() => setIsLoading(false));
  }, []);

  const selectedServers = activeBlacklist
    ? activeBlacklist.servers === null
      ? [t("records.blacklists.allServers")]
      : (activeBlacklist.servers || []).map(
          (number) =>
            servers[number] || t("records.blacklists.serverNumber", { number })
        )
    : [];
  const activeSyncLabel = activeBlacklist
    ? t(
        `records.blacklists.syncMethods.${activeBlacklist.sync}`,
        activeBlacklist.sync || t("common.unknown")
      )
    : "";
  const activeSyncDescription = activeBlacklist
    ? t(
        `records.blacklists.syncDescriptions.${activeBlacklist.sync}`,
        t("records.blacklists.unknownSyncDescription")
      )
    : "";

  const headerActions = (
    <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
      <BlacklistListCreateButton
        servers={servers}
        onSubmit={onBlacklistCreate}
      />
      <Button
        component={Link}
        to="/records/blacklists"
        variant="outlined"
        color="inherit"
        startIcon={<ArrowBackIcon />}
        sx={{ minHeight: 42, borderRadius: 0 }}
      >
        {t("records.blacklists.backToRecords")}
      </Button>
    </Stack>
  );

  return (
    <Stack spacing={1.5} sx={{ width: "100%", minWidth: 0, pb: 2 }}>
      <PageHeader
        eyebrow={t("records.blacklists.eyebrow")}
        title={t("records.blacklists.manageTitle")}
        subtitle={t("records.blacklists.manageSubtitle")}
        actions={headerActions}
      />

      {isLoading ? <LinearProgress /> : null}

      <BlacklistSyncReview />
      <BarricadeScanReview />

      <Box
        component="section"
        aria-label={t("records.blacklists.configuredLists")}
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            sm: "repeat(3, minmax(0, 1fr))",
          },
          gap: 1,
        }}
      >
        <Metric
          label={t("records.blacklists.listsTotal")}
          value={blacklists.length}
          icon={<SecurityOutlinedIcon />}
        />
        <Metric
          label={t("records.blacklists.globalLists")}
          value={globalListCount}
          icon={<DnsOutlinedIcon />}
        />
        <Metric
          label={t("records.blacklists.immediateLists")}
          value={immediateListCount}
          icon={<SyncAltIcon />}
        />
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "minmax(0, 1fr)",
            lg: "minmax(320px, .85fr) minmax(0, 1.15fr)",
          },
          gap: 1.5,
          alignItems: "start",
          minWidth: 0,
        }}
      >
        <Stack
          component="section"
          spacing={1}
          aria-labelledby="blacklist-list-title"
        >
          <Stack
            direction="row"
            alignItems="baseline"
            justifyContent="space-between"
          >
            <Typography id="blacklist-list-title" component="h2" variant="h6">
              {t("records.blacklists.configuredLists")}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {t("records.blacklists.selectListHint")}
            </Typography>
          </Stack>
          {blacklists.map((blacklist) => (
            <BlacklistListTile
              key={blacklist.id}
              servers={servers}
              blacklist={blacklist}
              selected={activeBlacklist?.id === blacklist.id}
              onSelect={setActiveBlacklist}
              onEdit={onEditBlacklist}
              onDelete={setDeleteCandidate}
            />
          ))}
          {!isLoading && !blacklists.length ? (
            <Paper variant="outlined" sx={{ borderRadius: 0, p: 3 }}>
              <Typography color="text.secondary" textAlign="center">
                {t("records.blacklists.noLists")}
              </Typography>
            </Paper>
          ) : null}
        </Stack>

        <Paper
          component="section"
          aria-labelledby="blacklist-detail-title"
          variant="outlined"
          sx={{
            borderRadius: 0,
            position: { lg: "sticky" },
            top: { lg: 68 },
            minWidth: 0,
            overflow: "hidden",
          }}
        >
          {activeBlacklist ? (
            <>
              <Stack
                direction={{ xs: "column", sm: "row" }}
                alignItems={{ xs: "stretch", sm: "flex-start" }}
                justifyContent="space-between"
                spacing={1.5}
                sx={{ p: 2, bgcolor: "action.selected" }}
              >
                <Box sx={{ minWidth: 0 }}>
                  <Typography variant="overline" color="primary.main">
                    {t("records.blacklists.selectedList")}
                  </Typography>
                  <Typography
                    id="blacklist-detail-title"
                    component="h2"
                    variant="h5"
                  >
                    {activeBlacklist.name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {t("records.blacklists.listId", { id: activeBlacklist.id })}
                  </Typography>
                </Box>
                <Stack direction="row" spacing={1}>
                  <Button
                    variant="contained"
                    startIcon={<EditOutlinedIcon />}
                    onClick={() => onEditBlacklist(activeBlacklist)}
                  >
                    {t("common.edit")}
                  </Button>
                  <Button
                    variant="outlined"
                    color="error"
                    startIcon={<DeleteOutlineIcon />}
                    onClick={() => setDeleteCandidate(activeBlacklist)}
                    disabled={activeBlacklist.id === 0}
                  >
                    {t("common.delete")}
                  </Button>
                </Stack>
              </Stack>

              <Stack spacing={2} sx={{ p: 2 }}>
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {t("records.blacklists.affectedServers")}
                  </Typography>
                  <Stack
                    direction="row"
                    spacing={0.75}
                    flexWrap="wrap"
                    useFlexGap
                    sx={{ mt: 0.75 }}
                  >
                    {selectedServers.length ? (
                      selectedServers.map((serverName) => (
                        <Chip
                          key={serverName}
                          size="small"
                          variant="outlined"
                          icon={<DnsOutlinedIcon />}
                          label={serverName}
                          sx={{ borderRadius: 0 }}
                        />
                      ))
                    ) : (
                      <Chip
                        size="small"
                        variant="outlined"
                        label={t("records.blacklists.noServers")}
                        sx={{ borderRadius: 0 }}
                      />
                    )}
                  </Stack>
                </Box>

                <Box>
                  <Typography variant="caption" color="text.secondary">
                    {t("records.blacklists.synchronization")}
                  </Typography>
                  <Typography sx={{ mt: 0.4, fontWeight: 700 }}>
                    {activeSyncLabel}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {activeSyncDescription}
                  </Typography>
                </Box>

                <Alert
                  severity={
                    activeBlacklist.servers?.length === 0 ? "warning" : "info"
                  }
                >
                  {activeBlacklist.servers?.length === 0
                    ? t("records.blacklists.warningNoServers")
                    : t("records.blacklists.changeImpact")}
                </Alert>
              </Stack>
            </>
          ) : (
            <Box sx={{ p: 4, textAlign: "center" }}>
              <Typography color="text.secondary">
                {t("records.blacklists.selectListHint")}
              </Typography>
            </Box>
          )}
        </Paper>
      </Box>

      <BlacklistListCreateDialog
        open={editDialogOpen}
        setOpen={setEditDialogOpen}
        servers={servers}
        onSubmit={onEditDialogSubmit}
        initialValues={editDialogInitialValues}
      />

      <Dialog
        open={deleteCandidate !== null}
        onClose={() => setDeleteCandidate(null)}
        aria-labelledby="delete-blacklist-title"
        aria-describedby="delete-blacklist-description"
        PaperProps={{
          sx: { borderRadius: 0, border: "1px solid", borderColor: "divider" },
        }}
      >
        <DialogTitle id="delete-blacklist-title">
          {deleteCandidate
            ? t("records.blacklists.deleteListTitle", {
                name: deleteCandidate.name,
              })
            : t("common.loading")}
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="delete-blacklist-description">
            {t("records.blacklists.deleteListDescription")}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteCandidate(null)} color="inherit">
            {t("common.cancel")}
          </Button>
          <Button
            onClick={() => {
              deleteBlacklist(deleteCandidate);
              setDeleteCandidate(null);
            }}
            color="error"
            variant="contained"
            startIcon={<DeleteOutlineIcon />}
            autoFocus
          >
            {t("common.delete")}
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
};

export default BlacklistLists;
