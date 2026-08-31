import { useCallback, useMemo, useState } from "react";
import {
  Box,
  Button,
  Divider,
  FormControl,
  IconButton,
  InputLabel,
  LinearProgress,
  MenuItem,
  Select,
  Stack,
  Tab,
  Tabs,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import ClearAllIcon from "@mui/icons-material/ClearAll";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import PlaylistAddCheckIcon from "@mui/icons-material/PlaylistAddCheck";
import UnfoldLessDoubleIcon from "@mui/icons-material/UnfoldLessDouble";
import UnfoldMoreDoubleIcon from "@mui/icons-material/UnfoldMoreDouble";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { extractPlayers, extractTeamState } from "@/utils/extractPlayers";
import { teamsLiveQueryOptions } from "@/queries/teams-live-query";
import {
  ActionButton,
  ActionMenu,
  ActionMenuButton,
} from "@/features/player-action/ActionMenu";
import {
  Actions,
  generatePlayerActions,
} from "@/features/player-action/actions";
import StickyContainer from "@/components/shared/StickyContainer";
import DisbandSquadDialog from "@/features/player-action/DisbandSquad";
import { DebouncedSearchInput } from "@/components/shared/DebouncedSearchInput";
import MessageAllDialog from "@/features/player-action/MessageAll";
import PageHeader from "@/components/shared/PageHeader";
import { useGlobalStore } from "@/stores/global-state";
import { useAppStore } from "@/stores/app-state";
import AutobalancerCard from "./autobalancer-card";
import BattleSummary from "./battle-summary";
import { LobbyContainer, TeamContainer } from "./styled";
import { TeamSection, UNASSIGNED } from "./team-section";

const FILTERS = ["all", "issues", "noLeader", "overCapacity", "unassigned"];

const PRIMARY_SELECTION_ACTIONS = [
  { action: Actions.SendMessage, labelKey: "message" },
  { action: Actions.KickPlayer, labelKey: "kick" },
  { action: Actions.AddBlacklist, labelKey: "ban" },
  { action: Actions.SwitchPlayer, labelKey: "switchTeam" },
  { action: Actions.RemoveFromSquad, labelKey: "removeFromSquad" },
];

const OVERFLOW_SELECTION_ACTIONS = generatePlayerActions({
  multiAction: true,
  onlineAction: true,
}).filter(
  (action) => action !== Actions.TempBan && action !== Actions.PermaBan
);

const SINGLE_PLAYER_ACTIONS = generatePlayerActions({
  multiAction: false,
  onlineAction: true,
});

const filterTeamRoster = (team, roleFilter, squadFilter) => {
  if (!team) return team;
  const matchesRole = (player) =>
    roleFilter === "all" || player?.role === roleFilter;
  const squads = Object.fromEntries(
    Object.entries(team.squads ?? {})
      .filter(([name]) => squadFilter === "all" || name === squadFilter)
      .map(([name, squad]) => [
        name,
        {
          ...squad,
          players: (squad.players ?? []).filter(matchesRole),
        },
      ])
      .filter(([, squad]) => squad.players.length > 0)
  );

  return {
    ...team,
    commander:
      squadFilter === "all" && matchesRole(team.commander)
        ? team.commander
        : null,
    squads,
  };
};

const TeamViewPage = () => {
  const { t } = useTranslation();
  const theme = useTheme();
  const singlePanel = useMediaQuery(theme.breakpoints.down("lg"));
  const { data: teams, isFetching } = useQuery({
    ...teamsLiveQueryOptions,
    staleTime: 5_000,
    refetchInterval: 10_000,
  });
  const gameState = useGlobalStore((state) => state.gameState);
  const openDrawer = useAppStore((state) => state.openDrawer);
  const [selectedPlayers, setSelectedPlayers] = useState(new Map());
  const [collapsedSquads, setCollapsedSquads] = useState({
    allies: {},
    axis: {},
    lobby: {},
  });
  const [searchTerm, setSearchTerm] = useState("");
  const [filterMode, setFilterMode] = useState("all");
  const [roleFilter, setRoleFilter] = useState("all");
  const [squadFilter, setSquadFilter] = useState("all");
  const [activeTeam, setActiveTeam] = useState("allies");
  const [autobalancerHighlights, setAutobalancerHighlights] = useState({});
  const [playerActionMenu, setPlayerActionMenu] = useState({
    anchorEl: null,
    player: null,
  });
  const openPlayerActionMenu = useCallback((anchorEl, player) => {
    setPlayerActionMenu({ anchorEl, player });
  }, []);
  const setPlayerActionMenuAnchor = useCallback((anchorEl) => {
    setPlayerActionMenu((current) => ({ ...current, anchorEl }));
  }, []);

  const summaryTeams = useMemo(
    () => ({
      allies: extractTeamState(teams?.allies, "allies"),
      axis: extractTeamState(teams?.axis, "axis"),
      lobby: extractTeamState(teams?.[UNASSIGNED], "lobby"),
    }),
    [teams]
  );

  const availableRoles = useMemo(() => {
    const roles = new Set();
    [teams?.allies, teams?.axis, teams?.[UNASSIGNED]].forEach((team) => {
      if (team?.commander?.role) roles.add(team.commander.role);
      Object.values(team?.squads ?? {}).forEach((squad) =>
        (squad.players ?? []).forEach((player) => {
          if (player.role) roles.add(player.role);
        })
      );
    });
    return Array.from(roles).sort();
  }, [teams]);

  const availableSquads = useMemo(() => {
    const squads = new Set();
    [teams?.allies, teams?.axis, teams?.[UNASSIGNED]].forEach((team) =>
      Object.keys(team?.squads ?? {}).forEach((name) => squads.add(name))
    );
    return Array.from(squads).sort();
  }, [teams]);

  const visibleTeams = useMemo(() => {
    const filteredAllies = filterTeamRoster(
      teams?.allies,
      roleFilter,
      squadFilter
    );
    const filteredAxis = filterTeamRoster(teams?.axis, roleFilter, squadFilter);
    const filteredLobby = filterTeamRoster(
      teams?.[UNASSIGNED],
      roleFilter,
      squadFilter
    );
    return {
      allies: extractTeamState(filteredAllies, "allies", searchTerm),
      axis: extractTeamState(filteredAxis, "axis", searchTerm),
      lobby: extractTeamState(filteredLobby, "lobby", searchTerm),
    };
  }, [roleFilter, searchTerm, squadFilter, teams]);

  const gameData = useMemo(() => {
    if (!gameState) return null;
    return {
      ...gameState,
      allies: { ...summaryTeams.allies, ...(teams?.allies ?? {}) },
      axis: { ...summaryTeams.axis, ...(teams?.axis ?? {}) },
      [UNASSIGNED]: {
        ...summaryTeams.lobby,
        ...(teams?.[UNASSIGNED] ?? {}),
      },
    };
  }, [gameState, summaryTeams, teams]);

  const allSquads = useMemo(() => {
    const result = { allies: new Set(), axis: new Set(), lobby: new Set() };
    Object.entries(summaryTeams).forEach(([teamName, team]) => {
      team.squads.forEach((squad) => result[teamName].add(squad.name));
      result[teamName].add(UNASSIGNED);
    });
    return result;
  }, [summaryTeams]);

  const anySquadCollapsed = Object.entries(allSquads).some(
    ([teamName, squads]) =>
      Array.from(squads).some(
        (squadName) => collapsedSquads[teamName]?.[squadName] ?? true
      )
  );

  const handleToggleExpand = (team, squadName) => {
    setCollapsedSquads((current) => ({
      ...current,
      [team]: {
        ...current[team],
        [squadName]: !(current[team]?.[squadName] ?? true),
      },
    }));
  };

  const setAllCollapsed = (collapsed, teamName) => {
    const names = teamName ? [teamName] : Object.keys(allSquads);
    setCollapsedSquads((current) => {
      const next = { ...current };
      names.forEach((name) => {
        next[name] = Object.fromEntries(
          Array.from(allSquads[name]).map((squadName) => [squadName, collapsed])
        );
      });
      return next;
    });
  };

  const handleTogglePlayer = (player, event) => {
    event?.stopPropagation?.();
    setSelectedPlayers((current) => {
      const next = new Map(current);
      if (next.has(player.player_id)) {
        next.delete(player.player_id);
      } else {
        next.set(player.player_id, {
          player_id: player.player_id,
          name: player.name,
        });
      }
      return next;
    });
  };

  const handleTogglePlayers = (players, shouldSelect) => {
    setSelectedPlayers((current) => {
      const next = new Map(current);
      players.forEach((player) => {
        if (shouldSelect) {
          next.set(player.player_id, {
            player_id: player.player_id,
            name: player.name,
          });
        } else {
          next.delete(player.player_id);
        }
      });
      return next;
    });
  };

  const handleToggleSquadSelection = (players, isSelected) =>
    handleTogglePlayers(players, !isSelected);

  const selectAllVisible = () => {
    const players = extractPlayers({
      allies: visibleTeams.allies,
      axis: visibleTeams.axis,
      [UNASSIGNED]: visibleTeams.lobby,
    });
    handleTogglePlayers(players, true);
  };

  const getTeamSection = (teamName) => {
    const team = visibleTeams[teamName];
    const summary = summaryTeams[teamName];
    return (
      <TeamSection
        key={teamName}
        team={team}
        title={t(`views.team.${teamName === "lobby" ? "lobby" : teamName}`)}
        selectedPlayers={selectedPlayers}
        onTogglePlayer={handleTogglePlayer}
        onToggleSquad={handleToggleSquadSelection}
        onToggleAll={handleTogglePlayers}
        collapsedSquads={collapsedSquads[teamName]}
        onToggleExpand={(squadName) => handleToggleExpand(teamName, squadName)}
        onTeamExpand={() => setAllCollapsed(false, teamName)}
        onTeamCollapse={() => setAllCollapsed(true, teamName)}
        filterMode={filterMode}
        commanderAvailable={Boolean(summary.commander)}
        activePlayerActionId={
          playerActionMenu.anchorEl ? playerActionMenu.player?.player_id : null
        }
        onOpenPlayerActionMenu={openPlayerActionMenu}
        highlightedPlayers={autobalancerHighlights}
      />
    );
  };

  const showLobby = summaryTeams.lobby.count > 0 || filterMode === "unassigned";
  const effectiveActiveTeam =
    activeTeam === "lobby" && !showLobby ? "allies" : activeTeam;

  return (
    <Box
      sx={{
        position: "relative",
        minHeight: "100%",
        width: "100%",
        minWidth: 0,
        pb: selectedPlayers.size ? 12 : 0,
      }}
    >
      <PageHeader
        eyebrow={t("views.team.eyebrow")}
        title={t("views.team.title")}
        subtitle={t("views.team.subtitle")}
      />

      <BattleSummary gameData={gameData} teams={summaryTeams} />
      <AutobalancerCard onHighlightPlayers={setAutobalancerHighlights} />

      <StickyContainer
        sx={{
          mb: 1.5,
          p: 1,
          border: "1px solid",
          borderColor: "divider",
          borderRadius: 1,
          backgroundColor: "background.paper",
          "& .MuiIconButton-root": { minWidth: 44, minHeight: 44 },
        }}
      >
        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={1}
          alignItems={{ md: "center" }}
        >
          <Box sx={{ minWidth: { md: 260 }, flex: 1 }}>
            <DebouncedSearchInput
              placeholder={t("views.team.searchPlayer")}
              initialValue={searchTerm}
              onChange={setSearchTerm}
            />
          </Box>
          <FormControl size="small" sx={{ minWidth: { md: 170 } }}>
            <InputLabel id="team-role-filter-label">
              {t("views.team.roleFilter")}
            </InputLabel>
            <Select
              labelId="team-role-filter-label"
              value={roleFilter}
              label={t("views.team.roleFilter")}
              onChange={(event) => setRoleFilter(event.target.value)}
            >
              <MenuItem value="all">{t("views.team.allRoles")}</MenuItem>
              {availableRoles.map((role) => (
                <MenuItem key={role} value={role}>
                  {t(`settings.configForms.roles.${role}`, {
                    defaultValue: role,
                  })}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: { md: 170 } }}>
            <InputLabel id="team-squad-filter-label">
              {t("views.team.squadFilter")}
            </InputLabel>
            <Select
              labelId="team-squad-filter-label"
              value={squadFilter}
              label={t("views.team.squadFilter")}
              onChange={(event) => setSquadFilter(event.target.value)}
            >
              <MenuItem value="all">{t("views.team.allSquads")}</MenuItem>
              {availableSquads.map((squad) => (
                <MenuItem key={squad} value={squad}>
                  {squad === UNASSIGNED ? t("views.team.noPlatoon") : squad}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: { md: 170 } }}>
            <InputLabel id="team-status-filter-label">
              {t("views.team.statusFilter")}
            </InputLabel>
            <Select
              labelId="team-status-filter-label"
              value={filterMode}
              label={t("views.team.statusFilter")}
              onChange={(event) => setFilterMode(event.target.value)}
            >
              {FILTERS.map((filter) => (
                <MenuItem key={filter} value={filter}>
                  {t(`views.team.filters.${filter}`)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Divider
            flexItem
            orientation="vertical"
            sx={{ display: { xs: "none", md: "block" } }}
          />
          <Stack direction="row" spacing={0.5} alignItems="center">
            <MessageAllDialog />
            <DisbandSquadDialog />
            <Tooltip disableInteractive title={t("common.selectAll")}>
              <IconButton
                aria-label={t("common.selectAll")}
                onClick={selectAllVisible}
                sx={{ minWidth: 44, minHeight: 44 }}
              >
                <PlaylistAddCheckIcon />
              </IconButton>
            </Tooltip>
            <Tooltip
              disableInteractive
              title={
                anySquadCollapsed
                  ? t("views.team.expandAll")
                  : t("views.team.collapseAll")
              }
            >
              <IconButton
                aria-label={
                  anySquadCollapsed
                    ? t("views.team.expandAll")
                    : t("views.team.collapseAll")
                }
                onClick={() => setAllCollapsed(!anySquadCollapsed)}
                sx={{ minWidth: 44, minHeight: 44 }}
              >
                {anySquadCollapsed ? (
                  <UnfoldMoreDoubleIcon />
                ) : (
                  <UnfoldLessDoubleIcon />
                )}
              </IconButton>
            </Tooltip>
          </Stack>
        </Stack>
        <Box sx={{ height: 2, mx: -1, mb: -1, mt: 0.75 }}>
          {isFetching && <LinearProgress sx={{ height: 2 }} />}
        </Box>
      </StickyContainer>

      {singlePanel && (
        <Tabs
          value={effectiveActiveTeam}
          onChange={(_, value) => setActiveTeam(value)}
          variant="fullWidth"
          sx={{ mb: 1.5, borderBottom: "1px solid", borderColor: "divider" }}
        >
          <Tab
            value="allies"
            label={`${t("views.team.allies")} · ${summaryTeams.allies.count}`}
          />
          <Tab
            value="axis"
            label={`${t("views.team.axis")} · ${summaryTeams.axis.count}`}
          />
          {showLobby && (
            <Tab
              value="lobby"
              label={`${t("views.team.lobby")} · ${summaryTeams.lobby.count}`}
            />
          )}
        </Tabs>
      )}

      {singlePanel ? (
        effectiveActiveTeam === "lobby" ? (
          <LobbyContainer>{getTeamSection("lobby")}</LobbyContainer>
        ) : (
          <TeamContainer>{getTeamSection(effectiveActiveTeam)}</TeamContainer>
        )
      ) : (
        <>
          {showLobby && (
            <LobbyContainer>{getTeamSection("lobby")}</LobbyContainer>
          )}
          <TeamContainer>
            {getTeamSection("allies")}
            {getTeamSection("axis")}
          </TeamContainer>
        </>
      )}

      {playerActionMenu.player ? (
        <ActionMenu
          actions={SINGLE_PLAYER_ACTIONS}
          recipients={playerActionMenu.player}
          withProfile
          anchorEl={playerActionMenu.anchorEl}
          setAnchorEl={setPlayerActionMenuAnchor}
          menuId="team-player-row-actions-menu"
        />
      ) : null}

      {selectedPlayers.size > 0 && (
        <Box
          role="region"
          aria-label={t("views.team.selectionActions")}
          sx={{
            position: "fixed",
            left: { xs: 8, lg: openDrawer ? 268 : 16 },
            right: { xs: 8, sm: 16 },
            bottom: { xs: 8, sm: 12 },
            zIndex: (theme) => theme.zIndex.drawer + 1,
            mx: "auto",
            width: "auto",
            maxWidth: 1180,
            minHeight: 68,
            px: { xs: 1, sm: 1.5 },
            py: { xs: 0.75, sm: 1 },
            display: "flex",
            alignItems: "center",
            gap: { xs: 0.75, sm: 1.25 },
            border: "1px solid",
            borderColor: "primary.main",
            borderRadius: 1,
            backgroundColor: "background.paper",
            boxShadow: 8,
          }}
        >
          <Box
            sx={{
              minWidth: 0,
              flex: { xs: "0 0 auto", sm: "0 0 168px" },
            }}
          >
            <Typography variant="subtitle2">
              {t("views.team.selected", { count: selectedPlayers.size })}
            </Typography>
            <Typography
              variant="caption"
              color="text.secondary"
              noWrap
              sx={{ display: { xs: "none", sm: "block" } }}
            >
              {t("views.team.selectionHint")}
            </Typography>
          </Box>
          <Divider
            flexItem
            orientation="vertical"
            sx={{ display: { xs: "none", sm: "block" } }}
          />
          <Stack
            direction="row"
            divider={<Divider flexItem orientation="vertical" />}
            sx={{
              flex: 1,
              minWidth: 0,
              overflowX: "auto",
              scrollbarWidth: "thin",
              "& > span": { flex: "0 0 auto" },
            }}
          >
            {PRIMARY_SELECTION_ACTIONS.map(({ action, labelKey }) => (
              <ActionButton
                key={action.name}
                action={action}
                recipients={Array.from(selectedPlayers.values())}
                label={t(`views.team.selectionActionLabels.${labelKey}`)}
                variant="text"
                sx={{
                  minHeight: 44,
                  px: { xs: 0.75, sm: 1 },
                  whiteSpace: "nowrap",
                  color: "text.primary",
                  "& .MuiButton-startIcon": {
                    mr: { xs: 0.5, sm: 0.75 },
                  },
                }}
              />
            ))}
            <ActionMenuButton
              actions={OVERFLOW_SELECTION_ACTIONS}
              recipients={Array.from(selectedPlayers.values())}
              orientation="horizontal"
              renderButton={(buttonProps) => (
                <Button
                  {...buttonProps}
                  variant="text"
                  startIcon={<MoreHorizIcon />}
                  sx={{
                    minHeight: 44,
                    px: { xs: 1, sm: 1.25 },
                    whiteSpace: "nowrap",
                    color: "text.primary",
                  }}
                >
                  <Box
                    component="span"
                    sx={{ display: { xs: "none", xl: "inline" } }}
                  >
                    {t("views.team.moreActions")}
                  </Box>
                </Button>
              )}
            />
          </Stack>
          <Button
            startIcon={<ClearAllIcon />}
            onClick={() => setSelectedPlayers(new Map())}
            variant="outlined"
            sx={{
              minHeight: 44,
              flex: "0 0 auto",
              whiteSpace: "nowrap",
              display: { xs: "none", sm: "inline-flex" },
            }}
          >
            {t("common.unselectAll")}
          </Button>
          <Tooltip disableInteractive title={t("common.unselectAll")}>
            <IconButton
              aria-label={t("common.unselectAll")}
              onClick={() => setSelectedPlayers(new Map())}
              sx={{
                minWidth: 44,
                minHeight: 44,
                flex: "0 0 auto",
                display: { xs: "inline-flex", sm: "none" },
              }}
            >
              <ClearAllIcon />
            </IconButton>
          </Tooltip>
        </Box>
      )}
    </Box>
  );
};

export default TeamViewPage;
