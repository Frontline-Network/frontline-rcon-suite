import React from "react";
import { Box, Typography } from "@mui/material";
import { Skeleton } from '@mui/material';
import moment from "moment";
import "moment/locale/de";
import { useTranslation } from "react-i18next";


export function PlayerVipSummary({ player, vipExpiration }) {
  const { t, i18n } = useTranslation();

  if (!player) {
    return (
      <>
        <Skeleton animation="wave" />
        <Skeleton animation="wave" />
        <Skeleton animation="wave" />
      </>
    )
  }

  return (
    <Box style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
      <Typography>{t("records.vips.name")}: <span style={{ fontWeight: 500 }}>{getPlayerNames(player, t)}</span></Typography>
      <Typography>{t("records.vips.playerId")}: <span style={{ fontWeight: 500 }}>{player.get("player_id")}</span></Typography>
      <Typography>{t("records.vips.expiration")}: <span style={{ fontWeight: 500 }}>{getExpirationDate(vipExpiration, i18n.resolvedLanguage)}</span></Typography>
    </Box>
  );
}

function getExpirationDate(vipExpiration, language) {
  const expiration = moment(vipExpiration).locale(language);
  return vipExpiration ? `${expiration.format("lll")} (${expiration.fromNow()})` : "/"
}

function getPlayerNames(player, t) {
  let output = t("sharedOperations.noRecordedName");

  if (player?.get("names")) {
    output = player.get("names").map(details => details.get("name")).join(", ")
  }

  if (player?.get("name")) {
    output = player.get("name")
  }

  return output;
}
