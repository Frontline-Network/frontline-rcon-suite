import Grid from "@mui/material/Grid2";
import { isModerationAction } from "@/utils/player-warnings.mjs";
import { WithPopver } from "../../commonComponent";
import moment from "moment";
import "moment/locale/de";
import { List } from "immutable";
import { useTranslation } from "react-i18next";

function truncateString(str, num) {
  // If the length of str is less than or equal to num
  // just return str--don't truncate it.
  if (str.length <= num) {
    return str;
  }
  // Return str truncated with '...' concatenated to the end of str.
  return str.slice(0, num) + "...";
}

export const Penalites = ({ player }) => {
  const { t, i18n } = useTranslation();
  const actions = player.get("received_actions", new List()).filter((item) => isModerationAction(item.toJS()));
  return (
  <div>
    {actions.size < 1 ? t("sharedOperations.cleanRecord") : ""}
    {actions.map((action) => (
      <p>{`${action.get("action_type")} ${moment.utc(action.get("time")).local().locale(i18n.resolvedLanguage).format(
        t("common.logDateTimeFormat")
      )}: ${truncateString(action.get("reason"), 50)} ${t("sharedOperations.by", { name: action.get("by") })}`}</p>
    ))}
  </div>
  );
};

export const PlayerPenalties = ({ player }) => (
  <Grid container>
    <Grid size={12}>
      <WithPopver
        popoverContent={<Penalites player={player} />}
      >
        <small>
          {player
            .get("penalty_count")
            .map((v, k) => `${k}: ${v}`)
            .join(" ")}
        </small>
      </WithPopver>
    </Grid>
  </Grid>
);
