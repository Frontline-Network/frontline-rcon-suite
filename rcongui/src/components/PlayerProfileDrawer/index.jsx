import {
  Box,
  IconButton,
  Typography,
  Divider,
  Tabs,
  Tab,
  Stack,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  AccordionActions,
  Button,
  Skeleton,
  Paper,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
} from "@mui/material";
import { Close } from "@mui/icons-material";
import { TabContext, TabPanel } from "@mui/lab";
import dayjs from "dayjs";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import CloseIcon from "@mui/icons-material/Close";
import { usePlayerSidebar } from "@/hooks/usePlayerSidebar";
import { generatePlayerActions } from "@/features/player-action/actions";
import { ClientError } from "../shared/ClientError";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ProfileHeader,
  ProfileWrapper,
  ResponsiveDrawer,
  Message,
} from "@/components/player/profile/styled";
import PlayerProfileHeader from "../player/profile/Header";
import PlayerProfileSummary from "../player/profile/Summary";
import PlayerProfileStatusTags from "../player/profile/StatusTags";
import { ActionMenuButton } from "@/features/player-action/ActionMenu";

const Penalties = ({ punish, kick, tempBan, parmaBan }) => {
  const { t } = useTranslation();

  return <dl>
    <dt>{t("playerDrawer.penalties.punish")}</dt>
    <dd>{punish ?? 0}</dd>
    <dt>{t("playerDrawer.penalties.kick")}</dt>
    <dd>{kick ?? 0}</dd>
    <dt>{t("playerDrawer.penalties.tempBan")}</dt>
    <dd>{tempBan ?? 0}</dd>
    <dt>{t("playerDrawer.penalties.permaBan")}</dt>
    <dd>{parmaBan ?? 0}</dd>
  </dl>;
};

const ReceivedActions = ({ actions }) => {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const displayCount = expanded ? actions.length : 2;

  return (
    <>
      {actions.slice(0, displayCount).map((action, i) => (
        <Accordion square={true} key={action.action_type + i}>
          <AccordionSummary
            expandIcon={<ArrowDropDownIcon />}
            aria-controls={`panel${i}-content`}
            id={`panel${i}-header`}
          >
            <Box sx={{ display: "flex", flexDirection: "column" }}>
              <Typography variant="subtitle2">{action.action_type}</Typography>
              <Typography component={"span"} sx={{ fontSize: "0.7rem" }}>
                {action.by} | {dayjs(action.time).format("HH:MM DD.MM.YY")}
              </Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Typography>{action.reason}</Typography>
          </AccordionDetails>
        </Accordion>
      ))}
      <Accordion defaultExpanded>
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          aria-controls="panel-action-content"
          id="panel-action-header"
        >
          {t("playerDrawer.showAll")}
        </AccordionSummary>
        <AccordionDetails>
          {t("playerDrawer.actionsTotal", { count: actions.length })}
        </AccordionDetails>
        <AccordionActions>
          <Button onClick={() => setExpanded((prevState) => !prevState)}>
            {expanded ? t("common.hide") : t("common.show")}
          </Button>
        </AccordionActions>
      </Accordion>
    </>
  );
};

const Messages = ({ messages }) => {
  const { t } = useTranslation();
  return (
    <>
      {messages && messages.length ? (
        <Stack spacing={1.5}>
          {messages.map((message, index) => (
            <Message key={message.time}>
              <Typography component={"span"} sx={{ fontSize: "0.7rem" }}>
                {message.by} | {dayjs(message.time).format("HH:MM DD.MM.YY")}
              </Typography>
              <Typography>{message.reason}</Typography>
            </Message>
          ))}
        </Stack>
      ) : (
        <Box>
          <Typography variant="subtitle" component={"span"}>
            {t("playerDrawer.noMessages")}
          </Typography>
        </Box>
      )}
    </>
  );
};

const LoadingSkeleton = ({ onClose }) => (
  <DrawerBase onClose={onClose}>
    <Stack gap={2} justifyContent={"center"} alignItems={"center"}>
      <Skeleton variant="circular" width={40} height={40} />
      <Divider orientation="horizontal" flexItem />
      <Skeleton variant="rectangular" width={210} height={60} />
      <Skeleton variant="rounded" width={210} height={60} />
    </Stack>
  </DrawerBase>
);

const DrawerBase = ({ children, onClose }) => (
  <ProfileWrapper>
    <ProfileHeader>
      <IconButton
        sx={{
          position: "absolute",
          top: (theme) => theme.spacing(0.5),
          right: (theme) => theme.spacing(0.5),
        }}
        size="small"
        onClick={onClose}
      >
        <Close />
      </IconButton>
    </ProfileHeader>
    <Box component={"section"} sx={{ p: 2 }}>
      {children}
    </Box>
  </ProfileWrapper>
);

const ProfileNotFound = ({ onClose }) => (
  <DrawerBase onClose={onClose}>
    <Box
      sx={{
        display: "grid",
        alignContent: "center",
        height: "100%",
        width: "100%",
      }}
    >
      <Typography variant="h6" sx={{ textAlign: "center" }}>
        <ProfileNotFoundLabel />
      </Typography>
    </Box>
  </DrawerBase>
);

const ProfileNotFoundLabel = () => {
  const { t } = useTranslation();
  return t("playerDrawer.profileNotFound");
};

const ProfileError = ({ error, onClose }) => (
  <DrawerBase onClose={onClose}>
    <ClientError error={error} />
  </DrawerBase>
);

const PlayerDetails = ({ player, onClose }) => {
  const { t } = useTranslation();
  const [openedTab, setOpenedTab] = useState("profile");
  const handleTabChange = (event, newValue) => {
    setOpenedTab(newValue);
  };

  const profile = player.profile;
  const isOnline = player?.is_online;
  const isVip = player?.is_vip;
  const playerVip = player?.vip;
  const isWatched = profile?.is_watched;
  const isBlacklisted = profile?.is_blacklisted;
  const isBanned = profile?.is_banned;
  const actionList = generatePlayerActions({
    multiAction: false,
    onlineAction: isOnline,
  });
  const name = profile?.account?.name ?? player?.name ?? profile?.soldier?.name ?? "???";
  const avatar = profile?.steaminfo?.profile?.avatar;
  const country =
    profile?.account?.country ??
    profile?.country ??
    profile?.steaminfo?.country;
  const level = player?.level ?? player?.profile?.soldier?.level;
  const platform = player?.platform ?? player?.profile?.soldier?.platform;
  const clanTag = player?.clan_tag ?? player?.profile?.soldier?.clan_tag;

  return (
    <ProfileWrapper component={"article"}>
      <Box sx={{ paddingTop: 2, paddingLeft: 8 }}>
        <PlayerProfileHeader
          player={player}
          isOnline={isOnline}
          avatar={avatar}
          name={name}
          country={country}
          level={level}
          platform={platform}
          clanTag={clanTag}
        />
      </Box>
      <ActionMenuButton
        recipients={player}
        actions={actionList}
        sx={{
          position: "absolute",
          top: (theme) => theme.spacing(0.5),
          left: (theme) => theme.spacing(0.5),
        }}
      />
      {onClose && (
        <IconButton
          sx={{
            position: "absolute",
            top: (theme) => theme.spacing(1),
            right: (theme) => theme.spacing(0.5),
          }}
          size="small"
          onClick={onClose}
        >
          <CloseIcon />
        </IconButton>
      )}
      <Divider />
      <PlayerProfileStatusTags
        isVip={isVip}
        isWatched={isWatched}
        isBlacklisted={isBlacklisted}
        isBanned={isBanned}
      />
      <Divider />
      <TabContext value={openedTab}>
        <Box sx={{ borderBottom: 1, borderColor: "divider" }}>
          <Tabs
            value={openedTab}
            onChange={handleTabChange}
            variant="scrollable"
            scrollButtons="auto"
            aria-label={t("playerDrawer.details")}
          >
            <Tab label={t("playerDrawer.tabs.profile")} value="profile" />
            {isOnline && <Tab label={t("playerDrawer.tabs.game")} value="game" />}
            <Tab label={t("playerDrawer.tabs.admin")} value="admin" />
            <Tab
              label={t("playerDrawer.tabs.messages")}
              value="messages"
              disabled={
                profile.received_actions.filter(
                  (action) => action.action_type === "MESSAGE"
                ).length === 0
              }
            />
            <Tab
              label={t("playerDrawer.tabs.comments")}
              value="comments"
              disabled={player.comments.length === 0}
            />
            <Tab
              label={t("playerDrawer.tabs.bans")}
              value="bans"
              disabled={player.bans.length === 0}
            />
            <Tab label={t("playerDrawer.tabs.logs")} value="logs" disabled={true} />
          </Tabs>
        </Box>
        <TabPanel value="profile">
          <PlayerProfileSummary
            player={profile}
            country={player.country}
            firstSeen={profile.created ?? player.created}
            lastSeen={profile?.names[0]?.last_seen}
            sessionCount={profile.sessions_count ?? profile.sessions_count}
            flags={profile.flags ?? profile.flags}
            totalPlaytime={
              profile.total_playtime_seconds ?? profile.total_playtime_seconds
            }
            vip={playerVip}
            otherVips={profile.vips.filter(
              // if player is not VIP on this server, the 'playerVip' will be undefined
              (vip) => vip.server_number !== (playerVip?.server_number ?? -1)
            )}
            names={profile.names}
            watchlist={profile.watchlist}
          />
        </TabPanel>
        {isOnline && (
          <TabPanel value="game">
            <PlayerGameDetails player={player} />
          </TabPanel>
        )}
        <TabPanel value="admin">
          <Box component={"section"}>
            <Typography variant="h6" component={"h2"}>
              {t("playerDrawer.penalties.title")}
            </Typography>
            <Penalties
              punish={profile.penalty_count["PUNISH"]}
              kick={profile.penalty_count["KICK"]}
              tempBan={profile.penalty_count["TEMPBAN"]}
              parmaBan={profile.penalty_count["PERMABAN"]}
            />
          </Box>
          <Box component={"section"}>
            <Typography variant="h6" component={"h2"}>
              {t("playerDrawer.receivedActions")}
            </Typography>
            <ReceivedActions actions={profile.received_actions} />
          </Box>
        </TabPanel>
        <TabPanel value="messages">
          <Box component={"section"}>
            <Typography variant="h6" component={"h2"}>
              {t("playerDrawer.tabs.messages")}
            </Typography>
            <Messages
              messages={profile.received_actions.filter(
                (action) => action.action_type === "MESSAGE"
              )}
            />
          </Box>
        </TabPanel>
        <TabPanel value="comments">
          <Comments comments={player.comments} />
        </TabPanel>
        <TabPanel value="bans">
          <Bans bans={player.bans} />
        </TabPanel>
      </TabContext>
    </ProfileWrapper>
  );
};

const Comments = ({ comments }) => {
  const { t } = useTranslation();
  return (
    <Box component={"section"}>
      <Typography variant="h6" component={"h2"}>
        {t("playerDrawer.tabs.comments")}
      </Typography>
      <Stack sx={{ gap: 1 }}>
        {comments.map((comment) => (
          <Comment key={comment.id} comment={comment} />
        ))}
      </Stack>
    </Box>
  );
};

const Comment = ({ comment }) => {
  return (
    <Box component={Paper} sx={{ p: 1 }}>
      <Typography>{comment.content}</Typography>
      <Divider sx={{ my: 1 }} />
      <Typography sx={{ fontSize: "0.7rem" }} variant="subtitle2">
        {comment.by} | {dayjs(comment.creation_time).format("HH:MM DD.MM.YY")}
      </Typography>
    </Box>
  );
};

const Bans = ({ bans }) => {
  const { t } = useTranslation();
  return (
    <Box component={"section"}>
      <Typography variant="h6" component={"h2"}>
        {t("playerDrawer.tabs.bans")}
      </Typography>
      <Stack sx={{ gap: 1 }}>
        {bans.map((ban) => (
          <Ban key={ban.id} ban={ban} />
        ))}
      </Stack>
    </Box>
  );
};

const Ban = ({ ban }) => {
  return (
    <Box component={Paper} sx={{ p: 1 }}>
      <Typography variant="subtitle">{ban.type}</Typography>
      <Typography>{ban.reason}</Typography>
      <Divider sx={{ my: 1 }} />
      <Typography sx={{ fontSize: "0.7rem" }} variant="subtitle2">
        {ban.by} | {dayjs(ban.ban_time).format("HH:MM DD.MM.YY")}
      </Typography>
    </Box>
  );
};

const PlayerGameDetails = ({ player }) => {
  const { t } = useTranslation();
  const statLabels = {
    level: t("views.table.level"),
    unit_name: t("playerDrawer.stats.unit"),
    loadout: t("playerDrawer.stats.loadout"),
    team: t("views.table.team"),
    role: t("views.table.role"),
    kills: t("views.table.kills"),
    deaths: t("views.table.deaths"),
    combat: t("views.table.combat"),
    offense: t("views.table.offense"),
    defense: t("views.table.defense"),
    support: t("views.table.support"),
  };

  return (
    <Box component={"section"}>
      <Typography variant="h6" component={"h2"}>
        {t("playerDrawer.currentGameStats")}
      </Typography>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>{t("playerDrawer.stat")}</TableCell>
            <TableCell>{t("playerDrawer.value")}</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {[
            "level",
            "unit_name",
            "loadout",
            "team",
            "role",
            "kills",
            "deaths",
            "team_kills",
            "vehicle_kills",
            "vehicles_destroyed",
            "combat",
            "offense",
            "defense",
            "support",
          ].map((stat) => (
            <TableRow key={stat}>
              <TableCell>{statLabels[stat]}</TableCell>
              <TableCell>{player[stat] ?? "-"}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
};

export const PlayerDetailDrawer = () => {
  const { open, close, player, isLoading, profileError } = usePlayerSidebar();

  return (
    <ResponsiveDrawer
      variant="persistent"
      open={open}
      anchor="right"
      onClose={close}
    >
      {isLoading && !player ? (
        <LoadingSkeleton onClose={close} />
      ) : profileError ? (
        <ProfileError error={profileError} onClose={close} />
      ) : !!player ? (
        <PlayerDetails player={player} onClose={close} />
      ) : open && !player ? (
        <ProfileNotFound onClose={close} />
      ) : null}
    </ResponsiveDrawer>
  );
};
