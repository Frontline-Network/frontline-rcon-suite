import { useMemo } from "react";
import {
  Tabs,
  Tab,
  CardContent,
  Divider,
} from "@mui/material";
import {
  useLoaderData,
  useSubmit,
  Outlet,
  useLocation,
  useNavigate,
} from "react-router-dom";
import {
  ProfileContainer,
  MainContent,
  SummaryCard,
  DetailCard,
} from "./styled";
import PlayerProfileSummary from "@/components/player/profile/Summary";
import PlayerProfileHeader from "@/components/player/profile/Header";
import { generatePlayerActions } from "@/features/player-action/actions";
import PlayerProfileStatusTags from "@/components/player/profile/StatusTags";
import ReceivedActions from "./[detail]/received-actions";
import { useGlobalStore } from "@/stores/global-state";
import ProfileActions from "@/components/player/profile/Actions";
import { useTranslation } from "react-i18next";
import LinkedAccounts from "@/components/player/profile/LinkedAccounts";

const DETAIL_LINKS = [
  { path: "", label: "records.playerDetails.profile" },
  { path: "actions", label: "records.playerDetails.actions" },
  { path: "sessions", label: "records.playerDetails.sessions" },
  { path: "names", label: "records.playerDetails.names" },
  { path: "comments", label: "records.playerDetails.comments" },
  { path: "logs", label: "records.playerDetails.logs" },
];

export default function PlayerProfilePage() {
  const { t } = useTranslation();
  const { profile } = useLoaderData();
  const submit = useSubmit();
  const location = useLocation();
  const navigate = useNavigate();

  const onlinePlayers = useGlobalStore((state) => state.onlinePlayers) ?? [];
  const server = useGlobalStore((state) => state.serverState);
  const profileVips = profile?.vips ?? [];
  const profileNames = profile?.names ?? [];
  const profileSoldier = profile?.soldier ?? {};
  const thisOnlinePlayer = useMemo(
    () =>
      onlinePlayers.find((player) => player.player_id === profile.player_id),
    [onlinePlayers, profile.player_id]
  );

  const playerVip = profileVips.find(
    (vip) => vip.server_number === server?.server_number
  );
  const isVip = thisOnlinePlayer?.is_vip || playerVip;
  const isWatched = profile?.watchlist && profile?.watchlist?.is_watched;
  const isBlacklisted = profile?.is_blacklisted;
  const isBanned = profile?.is_banned;
  const actionList = generatePlayerActions({
    multiAction: false,
    onlineAction: !!thisOnlinePlayer,
  });
  const name = profile?.account?.name ?? profileNames[0]?.name ?? profileSoldier.name ?? "???";
  const avatar = profile?.steaminfo?.profile?.avatar;
  const country = profile?.country ?? profile?.account?.country ?? profile?.steaminfo?.country
  const level = thisOnlinePlayer?.level ?? profile?.soldier?.level ?? 0
  const clanTag = thisOnlinePlayer?.clan_tag ?? profile?.soldier?.clan_tag
  const platform = thisOnlinePlayer?.platform ?? profile?.soldier?.platform

  const getActiveTab = () => {
    const path = location.pathname.split("/").pop();
    let activeTab = DETAIL_LINKS.findIndex((link) => link.path === path);
    if (path === profile.player_id) {
      activeTab = 0;
    }
    return activeTab;
  };

  const handleTabChange = (event, newValue) => {
    navigate(DETAIL_LINKS[newValue].path, { replace: true });
  };

  return (
    <ProfileContainer>
      <MainContent>
        <SummaryCard elevation={0} variant="outlined">
          <CardContent>
            <PlayerProfileHeader
              player={profile}
              isOnline={!!thisOnlinePlayer}
              ActionList={() => (
                <ProfileActions player={profile} actions={actionList} />
              )}
              avatar={avatar}
              name={name}
              country={country}
              level={level}
              clanTag={clanTag}
              platform={platform}
            />
            <LinkedAccounts identity={profile.identity} />
            <Divider />
            <PlayerProfileStatusTags
              isVip={isVip}
              isWatched={isWatched}
              isBlacklisted={isBlacklisted}
              isBanned={isBanned}
            />
            <Divider />
            <PlayerProfileSummary
              player={profile}
              country={profile.country}
              firstSeen={profile.created}
              lastSeen={profileNames[0]?.last_seen}
              sessionCount={profile.sessions_count}
              flags={profile.flags}
              totalPlaytime={profile.total_playtime_seconds}
              vip={profileVips.find(
                (vip) => vip.server_number === profile.server_number
              )}
              otherVips={profileVips.filter(
                (vip) =>
                  vip.server_number !==
                  (thisOnlinePlayer?.vip?.server_number ?? -1)
              )}
              names={profileNames}
              watchlist={profile.watchlist}
              eosId={profileSoldier.eos_id}
            />
          </CardContent>
        </SummaryCard>

        <DetailCard elevation={0} variant="outlined">
          <CardContent>
            <Tabs
              value={getActiveTab()}
              onChange={handleTabChange}
              variant="standard"
              sx={{ mb: 3 }}
            >
              {DETAIL_LINKS.map((link) => (
                <Tab key={link.path} label={t(link.label)} />
              ))}
            </Tabs>
            <Outlet context={{ profile, submit }} />
          </CardContent>
        </DetailCard>
      </MainContent>
    </ProfileContainer>
  );
}
