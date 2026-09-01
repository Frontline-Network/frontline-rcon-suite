import { cmd } from "@/utils/fetchUtils";
import { isFakeMode } from "@/mirage/demo-data";

const demoConfig = {
  enabled: true,
  default_method: "least_played_from_suggestions",
  number_last_played_to_exclude: 3,
  num_warfare_options: 4,
  num_offensive_options: 2,
  num_conquest_options: 0,
  num_domination_options: 0,
  num_skirmish_control_options: 1,
  consider_offensive_same_map: true,
  consider_skirmishes_as_same_map: true,
  consider_environment_as_same_map: false,
  allow_multiple_maps_with_same_environment: false,
  allow_consecutive_offensives: true,
  allow_consecutive_offensives_opposite_sides: false,
  allow_default_to_offensive: false,
  allow_consecutive_skirmishes: false,
  allow_default_to_skirmish: false,
  instruction_text:
    "Stimme über die nächste Karte ab:\n!votemap <Nummer>\n{map_selection}",
  thank_you_text:
    "Danke {player_name}. Deine Stimme für {map_name} wurde gezählt.",
  no_vote_text: "Es wurden noch keine gültigen Stimmen abgegeben.",
  reminder_frequency_minutes: 20,
  allow_opt_out: true,
  help_text: "Nutze !votemap <Nummer>, um über die nächste Karte abzustimmen.",
  vote_flags: [{ flag: "⭐", vote_count: 2 }],
  vote_ban_flags: [],
  player_choice_flags: ["🗺️"],
  player_choice_help_text:
    "Nutze !vm add <Karte> [Modus] [Umgebung], um eine Karte vorzuschlagen.",
  vip_vote_count: 2,
  remind_on_match_start: false,
  remind_on_match_end: true,
  allow_vip_only: false,
  allow_flag_only: [],
};

export const loader = async () => {
  if (isFakeMode()) return { config: demoConfig };
  return { config: await cmd.GET_VOTEMAP_CONFIG() };
};
