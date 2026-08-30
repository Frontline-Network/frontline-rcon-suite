import { cmd } from "@/utils/fetchUtils";
import { demoMapLayers, isFakeMode } from "@/mirage/demo-data";
import { redirect } from "react-router-dom";

export const loader = async () => {
  if (isFakeMode()) {
    const candidates = demoMapLayers.slice(0, 4);
    const voteCounts = [34, 22, 11, 6];
    const demoVoters = [
      { player_id: "76561198000000001", player_name: "FLN_Raven", count: 1 },
      { player_id: "76561198000000002", player_name: "FLN_Wolf", count: 1 },
      { player_id: "76561198000000003", player_name: "FLN_Valkyrie", count: 1 },
    ];
    return {
      votemapStatus: {
        enabled: true,
        paused: false,
        results: candidates.map((map, index) => ({
          map,
          voters: index === 0 ? demoVoters : [],
          votes_count: voteCounts[index],
        })),
        next_map: candidates[0]?.map?.pretty_name ?? null,
        last_reminder: new Date(Date.now() - 2 * 60_000).toISOString(),
        player_choice: candidates[0]
          ? {
              player_id: "76561198000000004",
              player_name: "Frontline Admin",
            }
          : null,
      },
      votemapResults: candidates[0]
        ? [
            {
              map: candidates[0].map,
              ts: Math.floor(Date.now() / 1000) - 3600,
              results: candidates.map((map, index) => ({
                map,
                votes_count: voteCounts[index],
              })),
            },
          ]
        : [],
    };
  }
  const permissions = await cmd.GET_PERMISSIONS();
  const granted = new Set(
    (permissions?.permissions ?? []).map((entry) =>
      typeof entry === "string" ? entry : entry.permission
    )
  );
  const canView = (...requiredPermissions) =>
    permissions?.is_superuser ||
    requiredPermissions.every((permission) => granted.has(permission));

  if (!canView("can_view_votemap_status")) {
    if (canView("can_view_map_whitelist", "can_view_all_maps")) {
      return redirect("/settings/maps/votemap/whitelist");
    }
    if (canView("can_view_votemap_config")) {
      return redirect("/settings/maps/votemap/settings");
    }
  }

  const votemapStatus = await cmd.GET_VOTEMAP_STATUS();
  const votemapResults = await cmd.GET_VOTEMAP_RESULTS();
  return { votemapStatus, votemapResults };
};
