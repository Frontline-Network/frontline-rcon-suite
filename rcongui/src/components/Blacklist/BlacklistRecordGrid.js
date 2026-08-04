import { Link as RouterLink } from "react-router-dom";
import {
  Avatar,
  ImageList,
  ImageListItem,
  IconButton,
  Link,
  List as MaterialList,
  ListItem,
  ListItemAvatar,
  ListItemSecondaryAction,
  ListItemText,
  Tooltip,
  Typography,
} from "@mui/material";
import Grid from "@mui/material/Grid2";
import FileCopyIcon from "@mui/icons-material/FileCopy";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";
import AnnouncementIcon from "@mui/icons-material/Announcement";
import makePlayerProfileUrl from "../../utils/makePlayerProfileUrl";
import { getCountry } from "../PlayersHistory/PlayerTile/PlayerHeader";
import { List } from "immutable";
import moment from "moment";
import "moment/locale/de";
import BlacklistRecordActionRow from "./BlacklistRecordActionRow";
import BlacklistRecordCreateDialog from "./BlacklistRecordCreateDialog";
import { handle_http_errors, postData, showResponse } from "@/utils/fetchUtils";
import {Fragment, useState} from "react";
import { useTranslation } from "react-i18next";

const BlacklistRecordTile = ({
  record,
  onEdit,
  onExpire,
  onDelete,
}) => {
  const { t, i18n } = useTranslation();
  const formatDuration = (milliseconds) => {
    const totalHours = Math.max(1, Math.round(Math.abs(milliseconds) / 3600000));
    if (totalHours >= 48) {
      const days = Math.round(totalHours / 24);
      return `${days} ${t(`common.timeUnits.${days === 1 ? "day" : "days"}`)}`;
    }
    return `${totalHours} ${t(`common.timeUnits.${totalHours === 1 ? "hour" : "hours"}`)}`;
  };
  const [showAll, setShowAll] = useState(false);
  const expiresAt = record.get("expires_at") ? moment(record.get("expires_at")) : null
  const isExpired = !record.get("is_active")
  const player = record.get("player");
  const playerNames = player.get("names", List());
  const firstName = playerNames.get(0) ? playerNames.get(0).get("name") : undefined;
  const firstNameLetter = (firstName || "?")[0];
  const hasMultipleNames = playerNames.size > 1;

  const steamProfile = player.get("steaminfo")
    ? player.get("steaminfo").get("profile")
    : new Map();
  const avatarUrl = steamProfile ? steamProfile.get("avatar") : undefined;
  const country = player.get("steaminfo")
    ? player.get("steaminfo").get("country", "")
    : "";

  const reason = record.get("formatted_reason")
  const createdAt = moment(record.get("created_at"));
  const now = moment();

  function getReportTemplate() {
    const template =
      `${t("records.blacklists.reportName")}: ${firstName || ""
      }\n${t("records.blacklists.playerId")}: ${player.get("player_id")
      }\nSteam URL: ${makePlayerProfileUrl(player.get("player_id"), firstName) || t("common.unknown")
      }\n${t("records.blacklists.issueType")}:\n${t("records.blacklists.description")}:\n${t("records.blacklists.evidence")}:`;
    return template;
  }

  return (
    (<Grid
      container
      style={isExpired ? { background: "linear-gradient(rgba(0, 0, 0, 0.05), rgba(0, 0, 0, 0.05))" } : {}}
      direction="column"
      justifyContent="space-between"
    >
      <MaterialList>
        <ListItem component={"div"} alignItems="flex-start" style={{ paddingBottom: 0 }}>
          <ListItemAvatar>
            <Link
              target="_blank"
              color="inherit"
              href={makePlayerProfileUrl(
                player.get("player_id"),
                firstName
              )}
            >
              <Avatar src={avatarUrl}>{firstNameLetter}</Avatar>
            </Link>
          </ListItemAvatar>
          <ListItemText
            primary={
              <Fragment>
                {showAll ? (
                  <Typography variant="body1">
                    {hasMultipleNames ? (
                      <IconButton
                        size="small"
                        color="primary"
                        onClick={() => setShowAll(false)}
                      >
                        <KeyboardArrowUpIcon fontSize="inherit" />
                      </IconButton>
                    ) : (
                      ""
                    )}
                    {playerNames.map((n) => n.get("name")).join(" | ")}
                  </Typography>
                ) : (
                  <Typography variant="body1">
                    {hasMultipleNames ? (
                      <IconButton
                        size="small"
                        color="primary"
                        onClick={() => setShowAll(true)}
                      >
                        <KeyboardArrowDownIcon fontSize="inherit" />
                      </IconButton>
                    ) : (
                      ""
                    )}
                    {firstName} {getCountry(country)}
                  </Typography>
                )}
              </Fragment>
            }
            secondary={
              <Link
                color="inherit"
                component={RouterLink}
                to={`/records/players/${player.get("player_id")}`}
              >
                {player.get("player_id")}
              </Link>
            }
          />
          <ListItemSecondaryAction>
            <Tooltip title={t("records.blacklists.copyPlayerId")}>
              <Typography variant="body2">
                <IconButton
                  size="small"
                  style={{ cursor: "pointer" }}
                  onClick={() => {
                    if (navigator.clipboard === undefined) {
                      alert(t("records.blacklists.clipboardHttps"));
                      return;
                    }
                    var text = player.get("player_id");
                    navigator.clipboard.writeText(text).then(
                      function () {
                        console.log("Async: Copying to clipboard was successful!");
                      },
                      function (err) {
                        console.error("Async: Could not copy text: ", err);
                      }
                    );
                  }}
                >
                  <FileCopyIcon fontSize="small" />
                </IconButton>
              </Typography>
            </Tooltip>
            <Tooltip title={t("records.blacklists.copyReport")}>
              <Typography variant="body2">
                <IconButton
                  size="small"
                  style={{ cursor: "pointer" }}
                  onClick={() => {
                    const text = getReportTemplate();
                    if (navigator.clipboard === undefined) {
                      alert(t("records.blacklists.clipboardHttps"));
                    } else {
                      navigator.clipboard.writeText(text).then(
                        function () {
                          console.log(
                            "Async: Copying to clipboard was successful!"
                          );
                        },
                        function (err) {
                          console.error("Async: Could not copy text: ", err);
                        }
                      );
                    }
                  }}
                >
                  <AnnouncementIcon fontSize="small" />
                </IconButton>
              </Typography>
            </Tooltip>
          </ListItemSecondaryAction>
        </ListItem>
      </MaterialList>
      <Typography variant={reason.length > 65 ? "body2" : "body1"}>
        {reason.length > 110
          ? reason.substring(0, 108) + "..."
          : reason
        }
      </Typography>
      <Grid
        container
        justifyContent="space-between"
        spacing={0}
        
      >
        <Grid
          container
          justifyContent="space-around"
          spacing={1}
        >
          <Grid>
            <Tooltip title={createdAt.format("LLLL")} arrow>
              <small>
                {t("records.blacklists.bannedAgo", {
                  duration: formatDuration(now.diff(createdAt)),
                  admin: record.get("admin_name") || t("common.unknown"),
                })}
              </small>
            </Tooltip>
          </Grid>
          <Grid>
            <Tooltip title={expiresAt ? expiresAt.locale(i18n.resolvedLanguage).format("LLLL") : t("records.blacklists.permanent")} arrow>
              <small>
                {expiresAt
                  ? (
                    now.isBefore(expiresAt)
                      ? t("records.blacklists.expiresIn", { duration: formatDuration(now.diff(expiresAt)) })
                      : t("records.blacklists.expiredAgo", { duration: formatDuration(now.diff(expiresAt)) })
                  )
                  : t("records.blacklists.neverExpires")
                }
              </small>
            </Tooltip>
          </Grid>
        </Grid>
        <BlacklistRecordActionRow
          isExpired={isExpired}
          onEdit={() => onEdit(record)}
          onExpire={() => {
            onExpire(record);
          }}
          onDelete={() => onDelete(record)}
        />
      </Grid>
    </Grid>)
  );
}

const BlacklistRecordGrid = ({
    blacklists,
    records,
    onRefresh,
  }) => {
    const { t } = useTranslation();
    const [editDialogOpen, setEditDialogOpen] = useState(false);
    const [editDialogInitialValues, setEditDialogInitialValues] = useState();

    function onEditRecord(record) {
      setEditDialogInitialValues({
        recordId: record.get("id"),
        blacklistId: record.get("blacklist").get("id"),
        playerId: record.get("player").get("player_id"),
        expiresAt: record.get("expires_at"),
        reason: record.get("reason"),
      })
      setEditDialogOpen(true);
    }

    function onEditDialogSubmit(data) {
      const recordId = editDialogInitialValues.recordId;
      postData(`${process.env.REACT_APP_API_URL}edit_blacklist_record`, {
        record_id: recordId,
        blacklist_id: data.blacklistId,
        player_id: data.playerId,
        expires_at: data.expiresAt,
        reason: data.reason,
      })
        .then((response) =>
          showResponse(response, `Record ${recordId} was edited`, true)
        )
        .then(result => result && !result.failed && onRefresh())
        .catch(handle_http_errors)
    }

    function onExpireRecord(record) {
      postData(`${process.env.REACT_APP_API_URL}edit_blacklist_record`, {
        record_id: record.get("id"),
        expires_at: moment().utc(),
      })
        .then((response) =>
          showResponse(response, `Record ${record.get("id")} was edited`, true)
        )
        .then(result => result && !result.failed && onRefresh())
        .catch(handle_http_errors)
    }

    function onDeleteRecord(record) {
      postData(`${process.env.REACT_APP_API_URL}delete_blacklist_record`, {
        record_id: record.get("id"),
      })
        .then((response) =>
          showResponse(response, `Record ${record.get("id")} was deleted`, true)
        )
        .then(result => result && !result.failed && onRefresh())
        .catch(handle_http_errors)
    }

    const size = {
      xs: 1,
      sm: 2,
      md: 3,
      lg: 4,
      xl: 5,
    }[2];

    return (
      (<Fragment>
        <Grid container>
          <Grid size={12}>
              <ImageList
                cols={size}
                spacing={12}
                sx={{ gridTemplateColumns: { xs: "1fr !important", md: "repeat(2, 1fr) !important" } }}
              >
              {records.map((record) => {
                return (
                  <ImageListItem
                    key={record.get("id")}
                  >
                    <BlacklistRecordTile
                      
                      record={record}
                      onEdit={onEditRecord}
                      onExpire={onExpireRecord}
                      onDelete={onDeleteRecord}
                    />
                  </ImageListItem>
                );
              })}
            </ImageList>
          </Grid>
        </Grid>
        <BlacklistRecordCreateDialog
          open={editDialogOpen}
          setOpen={setEditDialogOpen}
          blacklists={blacklists}
          initialValues={editDialogInitialValues}
          onSubmit={onEditDialogSubmit}
          titleText={t("records.blacklists.editRecord")}
          submitText={t("common.save")}
          disablePlayerId
        />
      </Fragment>)
    );
  }

export default BlacklistRecordGrid;
