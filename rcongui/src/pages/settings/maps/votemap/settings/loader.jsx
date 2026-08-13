import { cmd } from "@/utils/fetchUtils"
import { isFakeMode } from "@/mirage/demo-data"

export const loader = async () => {
    if (isFakeMode()) {
      return { config: { enabled: true, reminder_frequency_minutes: 5, num_warfare_options: 2, num_offensive_options: 1, num_conquest_options: 1, num_domination_options: 1, num_skirmish_control_options: 0, number_last_played_to_exclude: 2, default_method: "least_played_from_suggestions", instruction_text: "Stimme mit !votemap ab: {map_selection}", thank_you_text: "Danke {player_name}.", help_text: "Nutze !votemap <Nummer>." } }
    }
    const config = await cmd.GET_VOTEMAP_CONFIG()
    return { config }
}
