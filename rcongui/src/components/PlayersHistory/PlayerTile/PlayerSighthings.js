import Grid from "@mui/material/Grid2";
import Tooltip from "@mui/material/Tooltip";
import moment from "moment";
import "moment/locale/de";
import { useTranslation } from "react-i18next";

export const PlayerSighthings = ({ player }) => {
  const { t, i18n } = useTranslation();
  const language = i18n.resolvedLanguage;
  const first_seen = moment(player.get("first_seen_timestamp_ms")).locale(language);
  const last_seen = moment(player.get("last_seen_timestamp_ms")).locale(language);

  let vip_expiration;
  if (player.get("vip_expiration")) {
    vip_expiration = moment(player.get("vip_expiration")).locale(language);
  }

  const now = moment();
  const humanizedExpiration = moment
    .duration(now.diff(vip_expiration))
    .locale(language)
    .humanize();

  let vipDisplay;
  if (vip_expiration?.isBefore(moment.now())) {
    vipDisplay = (
      <small style={{ color: "red" }}>
        {t("sharedOperations.vipExpiredAgo", { duration: humanizedExpiration })}
      </small>
    );
  } else if (vip_expiration?.isSameOrAfter(moment().add(100, "years"))) {
    vipDisplay = <small>VIP · {t("records.vips.neverExpires")}</small>;
  } else if (vip_expiration) {
    vipDisplay = <small>{t("sharedOperations.vipExpiresIn", { duration: humanizedExpiration })}</small>;
  }

  return (
    (<Grid
        container
        justifyContent="space-between"
        spacing={0}
      >
      {vip_expiration ? (
        <Grid size={12}>
          <Tooltip title={vip_expiration.format("LLLL")} arrow>
            {vipDisplay}
          </Tooltip>
        </Grid>
      ) : (
        ""
      )}
      <Grid size={6}>
        <Tooltip title={first_seen.format("LLLL")} arrow>
          <small>
            {t("sharedOperations.firstSeenAgo", { duration: moment.duration(now.diff(first_seen)).locale(language).humanize() })}
          </small>
        </Tooltip>
      </Grid>
      <Grid size={6}>
        <Tooltip title={last_seen.format("LLLL")} arrow>
          <small>
            {t("sharedOperations.lastSeenAgo", { duration: moment.duration(now.diff(last_seen)).locale(language).humanize() })}
          </small>
        </Tooltip>
      </Grid>
    </Grid>)
  );
};
