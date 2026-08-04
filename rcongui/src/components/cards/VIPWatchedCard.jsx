import { useGlobalStore } from "@/stores/global-state";
import { useMemo } from "react";
import OnlineUsersCard from "@/components/shared/card/UsersCard";
import { useTranslation } from "react-i18next";

const VIPWatchedCard = () => {
  const { t } = useTranslation();
  const onlinePlayers = useGlobalStore((state) => state.onlinePlayers);

  const vips = useMemo(
    () =>
      onlinePlayers
        .filter((player) => player.is_vip)
        .map((player) => ({
          id: player.player_id,
          name: player.name,
          avatar: player.profile?.steaminfo?.profile?.avatar,
        })),
    [onlinePlayers]
  );

  const watchedPlayers = useMemo(
    () =>
      onlinePlayers
        .filter((player) => player?.profile?.watchlist?.is_watched)
        .map((player) => ({
          id: player.player_id,
          name: player.name,
          avatar: player.profile?.steaminfo?.profile?.avatar,
        })),
    [onlinePlayers]
  );

  return (
    <OnlineUsersCard
      title={t("dashboard.vipsWatched")}
      onlineUsers={[
        { group: "VIP", label: `VIP (${vips.length})`, users: vips },
        { group: "Watched", label: `${t("dashboard.watched")} (${watchedPlayers.length})`, users: watchedPlayers },
      ]}
    />
  );
};

export default VIPWatchedCard;
