import { cmd } from "@/utils/fetchUtils";
import { isFakeMode } from "@/mirage/demo-data";

export const loader = async () => {
  if (isFakeMode()) {
    return {
      settings: { autobalance_enabled: true, votekick_enabled: true, team_switch_cooldown: 15, autobalance_threshold: 3, idle_autokick_time: 15, max_ping_autokick: 250, queue_length: 6, vip_slots_num: 2, votekick_thresholds: [[0, 1], [25, 10], [50, 20], [75, 30]] },
      autokickSettings: { enabled: true, minimum_ingame_mods: 1, minimum_online_mods: 1, condition: "OR" },
    };
  }
  const settings = await cmd.GET_SERVER_SETTINGS();
  settings["votekick_thresholds"] = JSON.parse(settings["votekick_thresholds"]);
  const autokickSettings = await cmd.GET_VOTEKICK_AUTOTOGGLE_CONFIG();
  return { settings, autokickSettings };
};
