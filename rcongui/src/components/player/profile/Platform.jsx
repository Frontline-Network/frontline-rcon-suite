import React from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import VideogameAssetIcon from "@mui/icons-material/VideogameAsset";
import { Box, Chip } from "@mui/material";
import { getPlayerIdentity } from "@/utils/player-identity.mjs";
import EditSoldierButton from "./EditSoldierButton";
import {
  getPlatformIcon,
  getPlatformLabel,
} from "@/constants/platforms";

function PlatformChip({ platform, player, playerId, currentSoldierData }) {
  if (!platform)
    return (
      <EditSoldierButton
        Icon={VideogameAssetIcon}
        playerId={playerId}
        currentSoldierData={currentSoldierData}
      />
    );

  const icon = (
    <Box sx={{ width: 14, height: 24 }}>
      <FontAwesomeIcon icon={getPlatformIcon(platform)} size="xs" />
    </Box>
  );

  const identity = getPlayerIdentity({ ...player, platform, player_id: playerId ?? player?.player_id });
  if (identity.platform === "steam" && identity.profileUrl) {
    return (
      <Chip
        component={"a"}
        href={identity.profileUrl}
        target="_blank"
        rel="noopener noreferrer"
        icon={icon}
        label={getPlatformLabel(platform)}
        sx={{ "&:hover": { cursor: "pointer" } }}
      />
    );
  }

  return <Chip icon={icon} label={getPlatformLabel(platform)} />;
}

export default PlatformChip;
