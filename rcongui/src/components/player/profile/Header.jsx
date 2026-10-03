import { OnlineStatusBadge, ProfileHeader } from "./styled";
import { Avatar, Box, Typography, Stack } from "@mui/material";
import { Link } from "react-router-dom";
import PlayerIdentifiers from "./Identifiers";
import PlatformChip from "./Platform";
import CountryChip from "./Country";
import LevelChip from "./Level";
import LinksChip from "./Links";

const PlayerProfileHeader = ({
  player,
  isOnline,
  ActionList,
  headerActions,
  avatar,
  name,
  level,
  country,
  platform,
  clanTag,
  headingComponent = "h1",
}) => {
  const currentSoldierData = player?.soldier ?? player?.profile?.soldier;
  const playerId = player?.player_id ?? player?.profile?.player_id;
  const currentAccountData = player?.account ?? player?.profile?.account;
  return (
    <ProfileHeader
      sx={{
        minWidth: 0,
        containerType: "inline-size",
        containerName: "player-profile-header",
      }}
    >
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "minmax(0, 1fr) auto",
          gap: 1.5,
          alignItems: "start",
          "& > [data-testid='player-identifiers']": { gridColumn: "1 / -1" },
          "@container player-profile-header (min-width: 1050px)": {
            gridTemplateColumns: "minmax(240px, 1fr) minmax(680px, 1.7fr) auto",
            alignItems: "center",
            "& > [data-testid='player-identifiers']": {
              gridColumn: 2,
              gridRow: 1,
            },
            "& > .player-profile-actions": { gridColumn: 3 },
          },
        }}
      >
        <Stack direction="row" spacing={1.25} sx={{ minWidth: 0 }}>
          <OnlineStatusBadge
            overlap="circular"
            anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
            variant="dot"
            isOnline={isOnline}
            sx={{ alignSelf: "flex-start", flexShrink: 0 }}
          >
            <Avatar src={avatar} sx={{ width: 44, height: 44 }}>
              {name?.[0]}
            </Avatar>
          </OnlineStatusBadge>
          <Box sx={{ minWidth: 0 }}>
            <Typography
              component={headingComponent}
              sx={{
                fontSize: "1.125rem",
                fontWeight: 600,
                lineHeight: 1.35,
                mb: 0.75,
                overflowWrap: "anywhere",
                letterSpacing: 0,
              }}
            >
              <Link
                style={{ color: "inherit", textDecoration: "none" }}
                to={`/records/players/${playerId}`}
              >
                {name}
              </Link>
              {clanTag ? (
                <Typography
                  component="span"
                  variant="caption"
                  sx={{ ml: 0.75, color: "text.secondary", fontWeight: 400 }}
                >
                  [{clanTag}]
                </Typography>
              ) : null}
            </Typography>
            <Stack
              direction="row"
              gap={0.75}
              alignItems="center"
              flexWrap="wrap"
            >
              <LevelChip
                level={level}
                playerId={playerId}
                currentSoldierData={currentSoldierData}
              />
              <PlatformChip
                platform={platform}
                player={player}
                playerId={playerId}
                currentSoldierData={currentSoldierData}
              />
              <CountryChip
                country={country}
                playerId={playerId}
                currentAccountData={currentAccountData}
              />
              <LinksChip playerId={playerId} />
            </Stack>
          </Box>
        </Stack>
        <Box className="player-profile-actions">
          {headerActions ?? (ActionList && <ActionList />)}
        </Box>
        <PlayerIdentifiers player={player} platform={platform} />
      </Box>
    </ProfileHeader>
  );
};

export default PlayerProfileHeader;
