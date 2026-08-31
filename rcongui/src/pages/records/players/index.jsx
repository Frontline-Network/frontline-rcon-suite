import { cmd } from "@/utils/fetchUtils";
import {
  Button,
  Stack,
  Grid2 as Grid,
  Typography,
  Divider,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  useMediaQuery,
} from "@mui/material";
import ViewListIcon from "@mui/icons-material/ViewList";
import ViewModuleIcon from "@mui/icons-material/ViewModule";
import { useLoaderData, useNavigation } from "react-router-dom";
import { useMemo, useState, memo, useCallback, useEffect } from "react";
import PlayerCard from "@/components/shared/card/PlayerCard";
import PlayerRecordsList from "./PlayerRecordsList";
import NavPagination from "@/pages/stats/games/nav-pagination";
import { Box } from "@mui/material";
import { useGlobalStore } from "@/stores/global-state";
import { ActionBar } from "@/features/player-action/ActionMenu";
import { newRecordActions } from "@/features/player-action/actions";
import PlayerFiltersForm from "./PlayerFiltersForm";
import { useTranslation } from "react-i18next";
import PageHeader from "@/components/shared/PageHeader";
import { demoPlayerRecords, isFakeMode } from "@/mirage/demo-data";
import { useStorageState } from "@/hooks/useStorageState";

// Create a memoized version of PlayerCard
const MemoizedPlayerCard = memo(PlayerCard);

// Create a separate component for the players section
const PlayersGrid = memo(
  ({ players, selectedIds, handlePlayerSelect, ...props }) => {
    return (
      <Grid container spacing={1} {...props}>
        {players.map((player) => (
          <Grid
            key={player.player_id}
            size={{ xs: 12, md: 6, lg: 6, xl: 4 }}
            sx={{ "& > .MuiCard-root": { height: "100%", minWidth: 0 } }}
          >
            <MemoizedPlayerCard
              player={player}
              selected={selectedIds.has(player.player_id)}
              onSelect={handlePlayerSelect}
            />
          </Grid>
        ))}
      </Grid>
    );
  }
);

export const loader = async ({ request }) => {
  const url = new URL(request.url);

  const player_name = url.searchParams.get("player_name") ?? "";
  const player_id = url.searchParams.get("player_id") ?? "";

  const last_seen_from = url.searchParams.get("last_seen_from") ?? "";
  const last_seen_till = url.searchParams.get("last_seen_till") ?? "";

  const page = url.searchParams.get("page")
    ? Number(url.searchParams.get("page"))
    : 1;
  const page_size = url.searchParams.get("page_size")
    ? Number(url.searchParams.get("page_size"))
    : 50;

  const flags = url.searchParams.get("flags")
    ? url.searchParams.get("flags").split(",")
    : [];
  const country = url.searchParams.get("country") ?? "";

  const blacklisted = url.searchParams.get("blacklisted") ?? false;
  const exact_name_match = url.searchParams.get("exact_name_match") ?? false;
  const ignore_accent = url.searchParams.get("ignore_accent") ?? false;
  const is_watched = url.searchParams.get("is_watched") ?? false;

  const fields = {
    player_id,
    page,
    page_size,
    flags,
    blacklisted,
    exact_name_match,
    ignore_accent,
    is_watched,
    player_name,
    country,
    last_seen_from,
    last_seen_till,
  };

  // In the background, this command is POST request therefore the payload and not params
  const playersRecords = isFakeMode()
    ? {
        result: { players: demoPlayerRecords, total: demoPlayerRecords.length },
      }
    : await cmd.GET_PLAYERS_RECORDS({
        payload: Object.fromEntries(
          Object.entries(fields).filter(
            ([_, value]) => value !== "" && value !== null
          )
        ),
      });

  const bans = isFakeMode() ? [] : await cmd.GET_BANS();
  const bannedPlayerIds = new Set(bans.map((ban) => ban.player_id));

  return {
    players: playersRecords.result.players.map((player) => ({
      ...player,
      is_banned: bannedPlayerIds.has(player.player_id),
      identity: {
        ...(player.identity ?? {}),
        linked_accounts: (player.identity?.linked_accounts ?? []).map(
          (account) => ({
            ...account,
            is_banned: bannedPlayerIds.has(account.player_id),
          })
        ),
      },
    })),
    total_pages:
      page_size > 0
        ? Math.ceil(Number(playersRecords.result.total) / page_size)
        : 1,
    total: Number(playersRecords.result.total),
    page: Number(page),
    fields,
  };
};

export default function PlayersRecords() {
  const { t } = useTranslation();
  const {
    players: playersData,
    fields,
    total_pages,
    total,
    page,
  } = useLoaderData();
  const navigation = useNavigation();
  const isCompactViewport = useMediaQuery((theme) =>
    theme.breakpoints.down("md")
  );
  const server = useGlobalStore((state) => state.serverState);
  const onlinePlayers = useGlobalStore((state) => state.onlinePlayers) ?? [];
  const [selectedPlayerIds, setSelectedPlayerIds] = useState(new Set());
  // Cache player data by player_id to support multi-page selection
  const [playerCache, setPlayerCache] = useState(new Map());
  const [storedViewMode, setStoredViewMode] = useStorageState(
    "playerRecords.viewMode",
    "cards"
  );
  const viewMode = isCompactViewport ? "list" : storedViewMode;
  const onlinePlayersById = useMemo(
    () => new Map(onlinePlayers.map((player) => [player.player_id, player])),
    [onlinePlayers]
  );

  const players = useMemo(() => {
    if (!server) return playersData;
    return playersData.map((player) => {
      const thisOnlinePlayer = onlinePlayersById.get(player.player_id);

      const profile = {
        ...player,
        is_online: false,
        is_vip:
          player.vips &&
          player.vips.some((vip) => vip.server_number === server.server_number),
      };

      if (thisOnlinePlayer) {
        profile.is_online = true;
        profile.level = thisOnlinePlayer.level || player.soldier.level;
        profile.clan_tag = thisOnlinePlayer.clan_tag || player.soldier.clan_tag;
        profile.platform = thisOnlinePlayer.platform || player.soldier.platform;
      }

      return profile;
    });
  }, [playersData, server, onlinePlayersById]);

  // Update cache with current page players
  useEffect(() => {
    setPlayerCache((prevCache) => {
      const newCache = new Map(prevCache);
      for (const player of players) {
        newCache.set(player.player_id, player);
      }
      return newCache;
    });
  }, [players]);

  const handlePlayerSelect = useCallback((player) => {
    setSelectedPlayerIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(player.player_id)) {
        newSet.delete(player.player_id);
      } else {
        newSet.add(player.player_id);
      }
      return newSet;
    });
  }, []);

  const handleSelectAllPlayers = useCallback(() => {
    setSelectedPlayerIds((prev) => {
      // Check if all current page players are already selected
      const currentPageIds = new Set(players.map((p) => p.player_id));
      const allCurrentPageSelected = players.every((p) =>
        prev.has(p.player_id)
      );

      if (allCurrentPageSelected && players.length > 0) {
        // All current page players are selected, return unchanged
        return prev;
      }

      // Add all current page players to existing selection
      const newSet = new Set(prev);
      for (const player of players) {
        newSet.add(player.player_id);
      }
      return newSet;
    });
  }, [players]);

  const handleUnselectAllPlayers = () => {
    setSelectedPlayerIds(new Set());
  };

  const handleViewModeChange = (event, nextViewMode) => {
    if (nextViewMode) setStoredViewMode(nextViewMode);
  };

  // Convert Set to array of player objects for ActionBar
  // Uses cache to include players from all pages, not just current page
  const selectedPlayers = useMemo(() => {
    const result = [];
    for (const playerId of selectedPlayerIds) {
      const cachedPlayer = playerCache.get(playerId);
      if (cachedPlayer) {
        // Ensure the player has a name field for ActionForm
        const playerName =
          cachedPlayer.name ??
          cachedPlayer.account?.name ??
          cachedPlayer.names?.[0]?.name ??
          cachedPlayer.soldier?.name ??
          playerId;

        result.push({
          ...cachedPlayer,
          name: playerName,
          player_name: playerName, // Explicitly set player_name for actions
        });
      } else {
        // Fallback: create minimal player object if not in cache
        // This shouldn't happen often, but handles edge cases
        result.push({
          player_id: playerId,
          player_name: playerId,
          name: playerId,
          names: [{ name: playerId }],
        });
      }
    }
    return result;
  }, [selectedPlayerIds, playerCache]);

  return (
    <Stack
      spacing={1}
      sx={{
        mt: 2,
        pb: selectedPlayerIds.size ? { xs: 15, md: 0 } : 0,
        "& .MuiAlert-root": { borderRadius: 0 },
        "& .MuiButton-root": { borderRadius: 0 },
        "& .MuiCard-root": { borderRadius: 0 },
        "& .MuiChip-root": { borderRadius: 0 },
        "& .MuiIconButton-root": { borderRadius: 0 },
        "& .MuiOutlinedInput-root": { borderRadius: 0 },
        "& .MuiPaper-root": { borderRadius: 0 },
        "& .MuiToggleButton-root": { borderRadius: 0 },
      }}
    >
      <PageHeader
        eyebrow={t("records.players.eyebrow")}
        title={t("records.players.title")}
        subtitle={t("records.players.subtitle")}
      />
      {selectedPlayerIds.size > 0 ? (
        <Stack
          component="section"
          aria-label={t("records.players.selectionActions")}
          direction={{ xs: "column", md: "row" }}
          spacing={1}
          alignItems={{ xs: "stretch", md: "center" }}
          justifyContent="space-between"
          sx={{
            position: { xs: "fixed", md: "static" },
            left: { xs: 0, md: "auto" },
            right: { xs: 0, md: "auto" },
            bottom: { xs: 64, md: "auto" },
            zIndex: (theme) => theme.zIndex.appBar + 1,
            border: "1px solid",
            borderColor: "primary.dark",
            bgcolor: "background.paper",
            boxShadow: { xs: 8, md: 0 },
            p: 1,
          }}
        >
          <Stack
            direction="row"
            spacing={1}
            alignItems="center"
            justifyContent="space-between"
          >
            <Typography fontWeight={700}>
              {t("records.players.selected", {
                count: selectedPlayerIds.size,
              })}
            </Typography>
            <Button
              size="small"
              variant="outlined"
              color="inherit"
              onClick={handleUnselectAllPlayers}
            >
              {t("common.unselectAll")}
            </Button>
          </Stack>
          <Box sx={{ maxWidth: "100%", overflowX: "auto" }}>
            <ActionBar
              actions={newRecordActions}
              recipients={selectedPlayers}
            />
          </Box>
        </Stack>
      ) : null}
      <PlayerFiltersForm fields={fields} />
      <Stack
        component="section"
        id="players-section"
        spacing={1}
        sx={{ width: "100%" }}
      >
        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={1}
          alignItems={{ xs: "stretch", md: "center" }}
          justifyContent="space-between"
          sx={{
            border: (theme) => `1px solid ${theme.palette.divider}`,
            borderRadius: 0,
            bgcolor: "background.paper",
            px: 1.25,
            py: 1,
          }}
        >
          <Stack
            direction="row"
            spacing={1}
            alignItems="center"
            flexWrap="wrap"
            useFlexGap
          >
            <Typography fontWeight={600}>
              {t("records.players.results", { count: total })}
            </Typography>
            <Divider flexItem orientation="vertical" />
            <Typography color="text.secondary">
              {t("records.players.selected", { count: selectedPlayerIds.size })}
            </Typography>
            <Button
              size="small"
              variant="outlined"
              onClick={handleSelectAllPlayers}
            >
              {t("common.selectAll")}
            </Button>
            <Button
              size="small"
              variant="outlined"
              onClick={handleUnselectAllPlayers}
              disabled={selectedPlayerIds.size === 0}
            >
              {t("common.unselectAll")}
            </Button>
          </Stack>

          <Stack
            direction="row"
            spacing={1}
            alignItems="center"
            justifyContent="space-between"
          >
            <NavPagination
              page={page}
              maxPages={total_pages}
              disabled={navigation.state === "loading"}
            />
            {!isCompactViewport && (
              <ToggleButtonGroup
                exclusive
                size="small"
                value={viewMode}
                onChange={handleViewModeChange}
                aria-label={t("records.players.viewMode")}
              >
                <Tooltip title={t("records.players.cardView")}>
                  <ToggleButton
                    value="cards"
                    aria-label={t("records.players.cardView")}
                    sx={{ minWidth: 40, minHeight: 40 }}
                  >
                    <ViewModuleIcon />
                  </ToggleButton>
                </Tooltip>
                <Tooltip title={t("records.players.listView")}>
                  <ToggleButton
                    value="list"
                    aria-label={t("records.players.listView")}
                    sx={{ minWidth: 40, minHeight: 40 }}
                  >
                    <ViewListIcon />
                  </ToggleButton>
                </Tooltip>
              </ToggleButtonGroup>
            )}
          </Stack>
        </Stack>

        <Box
          aria-busy={navigation.state === "loading"}
          sx={{
            opacity: navigation.state === "loading" ? 0.55 : 1,
            transition: (theme) => theme.transitions.create("opacity"),
          }}
        >
          {viewMode === "list" ? (
            <PlayerRecordsList
              players={players}
              selectedIds={selectedPlayerIds}
              onSelect={handlePlayerSelect}
            />
          ) : (
            <PlayersGrid
              players={players}
              selectedIds={selectedPlayerIds}
              handlePlayerSelect={handlePlayerSelect}
            />
          )}
        </Box>

        <Box sx={{ flexGrow: 1 }} />
        <Stack direction="row" justifyContent="flex-end">
          <NavPagination
            page={page}
            maxPages={total_pages}
            disabled={navigation.state === "loading"}
          />
        </Stack>
      </Stack>
    </Stack>
  );
}
