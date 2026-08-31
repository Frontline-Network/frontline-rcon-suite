import { useMemo } from "react";
import {
  Box,
  Checkbox,
  Chip,
  Collapse,
  IconButton,
  Tooltip,
  Typography,
} from "@mui/material";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import PersonOffOutlinedIcon from "@mui/icons-material/PersonOffOutlined";
import ReportProblemOutlinedIcon from "@mui/icons-material/ReportProblemOutlined";
import StarIcon from "@mui/icons-material/Star";
import UnfoldLessIcon from "@mui/icons-material/UnfoldLess";
import UnfoldMoreIcon from "@mui/icons-material/UnfoldMore";
import { useTranslation } from "react-i18next";
import { secondsToTime } from "@/utils/extractPlayers";
import { TextButton } from "@/components/table/styles";
import { useThemedImages } from "@/hooks/useThemedImages";
import {
  CommanderRow,
  ContentWrapper,
  HeaderRow,
  PlayerRow,
  ScrollContainer,
  SquadGroupHeader,
  SquadHeader,
  TeamBox,
  TeamHeaderRow,
} from "./styled";

export const UNASSIGNED = "unassigned";

const LEADER_ROLES = new Set([
  "officer",
  "squadleader",
  "tankcommander",
  "spotter",
  "artilleryobserver",
  "mortarobserver",
  "helicopterlogisticsofficer",
]);

const SQUAD_LIMITS = {
  infantry: 6,
  armor: 3,
  armour: 3,
  recon: 2,
  artillery: 3,
  mortar: 3,
  helicopter: 6,
};

const normalizeType = (value) => String(value || "infantry").toLowerCase();

const getSquadCapacity = (squad) => SQUAD_LIMITS[normalizeType(squad?.type)];

const isSquadOverCapacity = (squad) => {
  const capacity = getSquadCapacity(squad);
  return Boolean(capacity && (squad?.players?.length ?? 0) > capacity);
};

const getLeader = (squad) =>
  squad.players.find((player) =>
    LEADER_ROLES.has(
      String(player.role || "")
        .replaceAll(" ", "")
        .toLowerCase()
    )
  );

const getKd = (player) => {
  const deaths = Number(player?.deaths || 0);
  return deaths
    ? (Number(player?.kills || 0) / deaths).toFixed(2)
    : Number(player?.kills || 0).toFixed(2);
};

const PlayerInfo = ({
  player,
  activePlayerActionId,
  onOpenPlayerActionMenu,
}) => {
  const { t } = useTranslation();
  const themedImg = useThemedImages();
  const actionMenuOpen = activePlayerActionId === player.player_id;

  return (
    <Box className="player-info">
      {player.role ? (
        <Box
          component="img"
          src={themedImg.getRoleIconSrc(player.role)}
          alt=""
          aria-hidden
          sx={{ width: 18, height: 18, flex: "0 0 auto" }}
        />
      ) : (
        <Box sx={{ width: 18, height: 18 }} />
      )}
      <TextButton
        aria-controls={
          actionMenuOpen ? "team-player-row-actions-menu" : undefined
        }
        aria-expanded={actionMenuOpen ? "true" : undefined}
        aria-haspopup="true"
        aria-label={t("actions.menu")}
        className="player-name"
        data-testid="team-player-action-trigger"
        onClick={(event) => onOpenPlayerActionMenu(event.currentTarget, player)}
      >
        {player.name}
      </TextButton>
      {player.is_vip && (
        <Tooltip title="VIP">
          <StarIcon color="primary" sx={{ fontSize: 16, flex: "0 0 auto" }} />
        </Tooltip>
      )}
    </Box>
  );
};

const PlayerRowWrapper = ({
  player,
  selected,
  isCommander = false,
  onToggle,
  activePlayerActionId,
  onOpenPlayerActionMenu,
}) => {
  const { t } = useTranslation();
  const Row = isCommander ? CommanderRow : PlayerRow;

  return (
    <Row selected={selected} level={player.level} isCommander={isCommander}>
      <Checkbox
        size="small"
        checked={selected}
        onChange={(event) => onToggle(player, event)}
        inputProps={{
          "aria-label": t("views.team.selectPlayer", { name: player.name }),
        }}
      />
      <PlayerInfo
        player={player}
        activePlayerActionId={activePlayerActionId}
        onOpenPlayerActionMenu={onOpenPlayerActionMenu}
      />
      <Typography className="leader-cell" variant="body2">
        {isCommander
          ? t("views.team.commander")
          : player.role
          ? t(`settings.configForms.roles.${player.role}`, {
              defaultValue: player.role,
            })
          : t("common.unknown")}
      </Typography>
      <Typography className="level-cell" variant="body2">
        {player.level ?? "–"}
      </Typography>
      <Typography className="problem-cell" variant="caption">
        {getKd(player)} ·{" "}
        {secondsToTime(
          player?.time ?? player?.profile?.current_playtime_seconds ?? 0
        )}
      </Typography>
    </Row>
  );
};

const SquadPlayers = ({
  squad,
  expanded,
  selectedPlayers,
  onTogglePlayer,
  activePlayerActionId,
  onOpenPlayerActionMenu,
}) => (
  <Collapse in={expanded} timeout="auto" unmountOnExit>
    {squad.players.map((player) => (
      <PlayerRowWrapper
        key={player.player_id}
        player={player}
        selected={selectedPlayers.has(player.player_id)}
        onToggle={onTogglePlayer}
        activePlayerActionId={activePlayerActionId}
        onOpenPlayerActionMenu={onOpenPlayerActionMenu}
      />
    ))}
  </Collapse>
);

const SquadRow = ({
  squad,
  expanded,
  selectedPlayers,
  onTogglePlayer,
  onToggleSquad,
  onToggleExpand,
  activePlayerActionId,
  onOpenPlayerActionMenu,
}) => {
  const { t } = useTranslation();
  const themedImg = useThemedImages();
  const type = normalizeType(squad.type);
  const leader = getLeader(squad);
  const allSelected =
    squad.players.length > 0 &&
    squad.players.every((player) => selectedPlayers.has(player.player_id));
  const partlySelected =
    squad.players.some((player) => selectedPlayers.has(player.player_id)) &&
    !allSelected;
  const hasLeaderProblem = !squad.has_leader || !leader;
  const capacity = getSquadCapacity(squad);
  const overCapacity = isSquadOverCapacity(squad);
  const problemLabels = [
    ...(hasLeaderProblem ? [t("views.team.noLeader")] : []),
    ...(overCapacity
      ? [
          t("views.team.squadOverCapacity", {
            count: squad.players.length,
            capacity,
          }),
        ]
      : []),
  ];
  const hasProblem = problemLabels.length > 0;

  return (
    <Box>
      <SquadHeader selected={allSelected} hasProblem={hasProblem}>
        <Checkbox
          size="small"
          checked={allSelected}
          indeterminate={partlySelected}
          onChange={() => onToggleSquad(squad.players, allSelected)}
          inputProps={{
            "aria-label": t("views.team.selectSquad", { name: squad.name }),
          }}
        />
        <Box className="squad-main">
          <Tooltip
            disableInteractive
            title={
              expanded
                ? t("views.team.collapseSquad")
                : t("views.team.expandSquad")
            }
          >
            <IconButton
              size="small"
              onClick={() => onToggleExpand(squad.name)}
              aria-label={
                expanded
                  ? t("views.team.collapseSquadNamed", { name: squad.name })
                  : t("views.team.expandSquadNamed", { name: squad.name })
              }
              aria-expanded={expanded}
              sx={{ minWidth: 44, minHeight: 44 }}
            >
              {expanded ? <ExpandMoreIcon /> : <ChevronRightIcon />}
            </IconButton>
          </Tooltip>
          <Box
            component="img"
            src={themedImg.getRoleIconSrc(type)}
            alt=""
            aria-hidden
            sx={{ width: 18, height: 18, flex: "0 0 auto" }}
          />
          <Typography className="squad-name" variant="body2">
            {squad.name}
          </Typography>
          <Chip
            size="small"
            variant="outlined"
            label={`${squad.players.length}${capacity ? `/${capacity}` : ""}`}
            color={
              overCapacity
                ? "warning"
                : capacity && squad.players.length === capacity
                ? "success"
                : "default"
            }
            sx={{ height: 22, flex: "0 0 auto" }}
          />
        </Box>
        <Typography className="leader-cell" variant="body2">
          {leader?.name ?? t("views.team.noLeader")}
        </Typography>
        <Typography className="level-cell" variant="body2">
          Ø {squad.level ?? 0}
        </Typography>
        <Tooltip disableInteractive title={problemLabels.join(" · ")}>
          <Box
            className="problem-cell"
            aria-label={
              hasProblem
                ? problemLabels.join(" · ")
                : t("views.team.noSquadProblems")
            }
          >
            {hasProblem ? (
              <>
                <ReportProblemOutlinedIcon fontSize="small" aria-hidden />
                <span>{problemLabels.length}</span>
              </>
            ) : (
              <CheckCircleOutlineIcon fontSize="small" aria-hidden />
            )}
          </Box>
        </Tooltip>
      </SquadHeader>
      <SquadPlayers
        squad={squad}
        expanded={expanded}
        selectedPlayers={selectedPlayers}
        onTogglePlayer={onTogglePlayer}
        activePlayerActionId={activePlayerActionId}
        onOpenPlayerActionMenu={onOpenPlayerActionMenu}
      />
    </Box>
  );
};

const MissingCommanderRow = () => {
  const { t } = useTranslation();
  return (
    <CommanderRow isCommander>
      <Box />
      <Box className="player-info" sx={{ color: "warning.main" }}>
        <PersonOffOutlinedIcon fontSize="small" aria-hidden />
        <Typography variant="body2" fontWeight={700}>
          {t("views.team.noCommander")}
        </Typography>
      </Box>
      <Typography className="leader-cell" variant="body2">
        {t("views.team.commanderPositionOpen")}
      </Typography>
      <Typography className="level-cell">–</Typography>
      <Box className="problem-cell" sx={{ color: "warning.main" }}>
        <ReportProblemOutlinedIcon fontSize="small" aria-hidden />
        <span>1</span>
      </Box>
    </CommanderRow>
  );
};

export const TeamSection = ({
  team,
  title,
  selectedPlayers,
  onTogglePlayer,
  onToggleSquad,
  onToggleAll,
  collapsedSquads = {},
  onToggleExpand,
  onTeamExpand,
  onTeamCollapse,
  filterMode = "all",
  commanderAvailable,
  activePlayerActionId,
  onOpenPlayerActionMenu,
}) => {
  const { t } = useTranslation();
  const isLobby = team.name === "lobby";

  const {
    commander,
    squadGroups,
    unassignedPlayers,
    visiblePlayers,
    issueCount,
  } = useMemo(() => {
    const allSquads = (team.squads ?? [])
      .filter((squad) => squad.name !== "command" && squad.name !== UNASSIGNED)
      .sort((a, b) => a.name.localeCompare(b.name));
    const unassigned =
      team.squads?.find((squad) => squad.name === UNASSIGNED)?.players ?? [];
    const leaderlessSquads = allSquads.filter(
      (squad) => !squad.has_leader || !getLeader(squad)
    );
    const overCapacitySquads = allSquads.filter(isSquadOverCapacity);
    const problemSquads = allSquads.filter(
      (squad) =>
        !squad.has_leader || !getLeader(squad) || isSquadOverCapacity(squad)
    );
    const visibleSquads =
      filterMode === "issues"
        ? problemSquads
        : filterMode === "noLeader"
        ? leaderlessSquads
        : filterMode === "overCapacity"
        ? overCapacitySquads
        : filterMode === "unassigned"
        ? []
        : allSquads;

    const grouped = visibleSquads.reduce((result, squad) => {
      const type = normalizeType(squad.type);
      result[type] ??= [];
      result[type].push(squad);
      return result;
    }, {});
    const preferredOrder = [
      "infantry",
      "armor",
      "armour",
      "recon",
      "artillery",
      "mortar",
      "helicopter",
    ];
    const typeOrder = [
      ...preferredOrder.filter((type) => grouped[type]?.length),
      ...Object.keys(grouped).filter((type) => !preferredOrder.includes(type)),
    ];
    const showUnassigned =
      filterMode === "all" ||
      filterMode === "issues" ||
      filterMode === "unassigned";
    const showCommander = filterMode === "all" || filterMode === "issues";
    const groups = typeOrder.map((type) => ({ type, squads: grouped[type] }));
    const players = [
      ...(showCommander && team.commander ? [team.commander] : []),
      ...groups.flatMap(({ squads }) =>
        squads.flatMap((squad) => squad.players)
      ),
      ...(showUnassigned ? unassigned : []),
    ];

    return {
      commander: showCommander ? team.commander : null,
      squadGroups: groups,
      unassignedPlayers: showUnassigned ? unassigned : [],
      visiblePlayers: players,
      issueCount:
        problemSquads.length +
        unassigned.length +
        (!isLobby && !commanderAvailable ? 1 : 0),
    };
  }, [commanderAvailable, filterMode, isLobby, team]);

  const allSelected =
    visiblePlayers.length > 0 &&
    visiblePlayers.every((player) => selectedPlayers.has(player.player_id));
  const partlySelected =
    visiblePlayers.some((player) => selectedPlayers.has(player.player_id)) &&
    !allSelected;
  const visibleSquadNames = [
    ...squadGroups.flatMap(({ squads }) => squads.map((squad) => squad.name)),
    ...(unassignedPlayers.length ? [UNASSIGNED] : []),
  ];
  const anySquadCollapsed = visibleSquadNames.some(
    (squadName) => collapsedSquads[squadName] ?? true
  );
  const renderedSquadCount = squadGroups.reduce(
    (sum, group) => sum + group.squads.length,
    0
  );

  const renderUnassigned = () => {
    if (!unassignedPlayers.length) return null;
    const squad = {
      name: UNASSIGNED,
      type: "infantry",
      has_leader: isLobby,
      level: 0,
      players: unassignedPlayers,
    };
    return (
      <>
        <SquadGroupHeader>
          {isLobby ? t("views.live.lobby") : t("views.team.noPlatoon")}
        </SquadGroupHeader>
        <SquadRow
          squad={squad}
          expanded={!(collapsedSquads[UNASSIGNED] ?? true)}
          selectedPlayers={selectedPlayers}
          onTogglePlayer={onTogglePlayer}
          onToggleSquad={onToggleSquad}
          onToggleExpand={onToggleExpand}
          activePlayerActionId={activePlayerActionId}
          onOpenPlayerActionMenu={onOpenPlayerActionMenu}
        />
      </>
    );
  };

  return (
    <TeamBox teamName={team.name} data-testid={`team-panel-${team.name}`}>
      <TeamHeaderRow>
        <Checkbox
          size="small"
          checked={allSelected}
          indeterminate={partlySelected}
          onChange={(event) =>
            onToggleAll(visiblePlayers, event.target.checked)
          }
          inputProps={{
            "aria-label": t("views.team.selectTeam", { name: title }),
          }}
        />
        <Box className="team-title">
          <Typography
            variant="h6"
            component="h2"
            sx={{
              fontWeight: 800,
              color:
                team.name === "allies"
                  ? "info.light"
                  : team.name === "axis"
                  ? "error.light"
                  : "text.primary",
            }}
          >
            {title}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t("views.team.totalPlayers", { count: team.count })}
          </Typography>
        </Box>
        <Box className="team-summary">
          <Typography variant="caption" className="optional-summary">
            {t("views.team.squadsCount", { count: renderedSquadCount })}
          </Typography>
          <Typography variant="caption" className="optional-summary">
            Ø {team.avg_level ?? 0}
          </Typography>
          <Chip
            size="small"
            color={issueCount ? "warning" : "success"}
            variant="outlined"
            label={t("views.team.problemsCount", { count: issueCount })}
          />
          <Tooltip
            disableInteractive
            title={
              anySquadCollapsed
                ? t("views.team.expandTeam")
                : t("views.team.collapseTeam")
            }
          >
            <IconButton
              onClick={anySquadCollapsed ? onTeamExpand : onTeamCollapse}
              aria-label={
                anySquadCollapsed
                  ? t("views.team.expandTeamNamed", { name: title })
                  : t("views.team.collapseTeamNamed", { name: title })
              }
              sx={{ minWidth: 44, minHeight: 44 }}
            >
              {anySquadCollapsed ? <UnfoldMoreIcon /> : <UnfoldLessIcon />}
            </IconButton>
          </Tooltip>
        </Box>
      </TeamHeaderRow>

      <ScrollContainer>
        <ContentWrapper>
          <HeaderRow aria-hidden>
            <Box />
            <Box>
              {isLobby ? t("views.table.name") : t("views.team.squadOrPlayer")}
            </Box>
            <Box className="leader-cell">{t("views.team.leaderOrRole")}</Box>
            <Box className="level-cell">{t("views.table.level")}</Box>
            <Box>{t("views.team.statusOrKd")}</Box>
          </HeaderRow>

          {!isLobby &&
            (filterMode === "all" || filterMode === "issues") &&
            (commander ? (
              <PlayerRowWrapper
                player={commander}
                selected={selectedPlayers.has(commander.player_id)}
                onToggle={onTogglePlayer}
                isCommander
                activePlayerActionId={activePlayerActionId}
                onOpenPlayerActionMenu={onOpenPlayerActionMenu}
              />
            ) : !commanderAvailable ? (
              <MissingCommanderRow />
            ) : null)}

          {renderUnassigned()}

          {squadGroups.map(({ type, squads }) => (
            <Box key={type}>
              <SquadGroupHeader>
                {t(`views.team.squadTypes.${type}`, {
                  defaultValue: t("views.team.squadTypes.other"),
                })}
              </SquadGroupHeader>
              {squads.map((squad) => (
                <SquadRow
                  key={squad.name}
                  squad={squad}
                  expanded={!(collapsedSquads[squad.name] ?? true)}
                  selectedPlayers={selectedPlayers}
                  onTogglePlayer={onTogglePlayer}
                  onToggleSquad={onToggleSquad}
                  onToggleExpand={onToggleExpand}
                  activePlayerActionId={activePlayerActionId}
                  onOpenPlayerActionMenu={onOpenPlayerActionMenu}
                />
              ))}
            </Box>
          ))}

          {!visiblePlayers.length &&
            !(!commanderAvailable && filterMode === "issues") && (
              <Box sx={{ p: 3, textAlign: "center", color: "text.secondary" }}>
                <Typography variant="body2">
                  {t("views.team.noMatches")}
                </Typography>
              </Box>
            )}
        </ContentWrapper>
      </ScrollContainer>
    </TeamBox>
  );
};
