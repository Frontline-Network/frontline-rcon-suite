import {
  faArrowRight,
  faCheckDouble,
  faChevronDown,
  faChevronRight,
  faCircleExclamation,
  faComments,
  faCopy,
  faCrosshairs,
  faFlag,
  faGavel,
  faGun,
  faSkull,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Box, Button, Stack, Tooltip, Typography, alpha } from "@mui/material";
import dayjs from "dayjs";
import { memo, useEffect, useId, useMemo, useRef, useState } from "react";
import { LogMessage } from "@/components/shared/LogMessage";
import { NoRowsOverlay } from "@/components/NoRowsOverlay";
import { useTranslation } from "react-i18next";
import CopyToClipboardButton from "@/components/shared/CopyToClipboardButton";
import { PlayerDrawerLink } from "@/components/shared/PlayerDrawerLink";
import { useGlobalStore } from "@/stores/global-state";
import { getLogTeam, removeLogPlayerIds } from "@/utils/lib";
import { getMessageBody, groupLogRows } from "./log-stacks.mjs";
import {
  getLogPresentation,
  matchesLogActions,
} from "./log-display-preferences.mjs";

let previousOnlinePlayerSource;
let previousOnlinePlayerContexts = [];

const selectOnlinePlayerContexts = (state) => {
  const source = state.onlinePlayers ?? [];
  if (source === previousOnlinePlayerSource)
    return previousOnlinePlayerContexts;

  previousOnlinePlayerSource = source;
  const next = source.map((player) => ({
    player_id: player.player_id,
    name: String(player.name ?? "").trim(),
    team: player.team,
    faction: player.faction,
  }));
  const unchanged =
    next.length === previousOnlinePlayerContexts.length &&
    next.every((player, index) => {
      const previous = previousOnlinePlayerContexts[index];
      return (
        player.player_id === previous.player_id &&
        player.name === previous.name &&
        player.team === previous.team &&
        player.faction === previous.faction
      );
    });

  if (!unchanged) previousOnlinePlayerContexts = next;
  return previousOnlinePlayerContexts;
};

const getEventMeta = (action = "") => {
  if (action === "TEAM KILL" || action.startsWith("TK ")) {
    return {
      labelKey: "teamkills",
      color: "error",
      icon: faSkull,
    };
  }
  if (action.startsWith("ADMIN")) {
    return { labelKey: "admin", color: "secondary", icon: faGavel };
  }
  if (action.startsWith("CHAT")) {
    return { labelKey: "chat", color: "info", icon: faComments };
  }
  if (action.startsWith("MATCH")) {
    return { labelKey: "match", color: "success", icon: faFlag };
  }
  if (action === "KILL") {
    return { labelKey: "kills", color: "warning", icon: faCrosshairs };
  }
  return {
    label: action,
    color: "primary",
    icon: faCircleExclamation,
  };
};

const normalizeTeam = (event, fallbackTeam) => {
  const explicitTeam = String(
    event.team ??
      event.player_team ??
      event.player_team_1 ??
      event.team_name ??
      fallbackTeam ??
      ""
  ).toLowerCase();

  if (explicitTeam.includes("allies")) return "Allies";
  if (explicitTeam.includes("axis")) return "Axis";
  return getLogTeam(event);
};

const canonicalTeam = (value) => {
  const normalized = String(value ?? "")
    .trim()
    .toLowerCase();
  if (normalized.includes("allies")) return "Allies";
  if (normalized.includes("axis")) return "Axis";
  return undefined;
};

const getEventPlayerTeams = (event, fallbackTeam1, fallbackTeam2) => {
  const transportText = [
    event.message,
    event.line_without_time,
    event.raw,
  ].join(" ");
  const transportTeams = [
    ...transportText.matchAll(/\((allies|axis)\s*\//gi),
  ].map((match) => canonicalTeam(match[1]));
  const team1 = normalizeTeam(event, fallbackTeam1) ?? transportTeams[0];
  const explicitTeam2 = canonicalTeam(
    event.team_2 ?? event.player_team_2 ?? event.player_2_team
  );
  const detectedTeam2 =
    explicitTeam2 ??
    transportTeams[1] ??
    canonicalTeam(fallbackTeam2) ??
    (event.action === "TEAM KILL" ? team1 : undefined);
  const team2 =
    event.action === "KILL" && team1 && detectedTeam2 === team1
      ? team1 === "Axis"
        ? "Allies"
        : "Axis"
      : detectedTeam2;

  return [team1, team2];
};

const getWeaponName = (event, rawText) => {
  const explicitWeapon = String(event.weapon ?? "").trim();
  if (explicitWeapon) return explicitWeapon;

  // Older HLL and early HLLV log records may only contain the weapon in the
  // raw message. Keep that value verbatim instead of relying on a game catalog.
  return rawText.match(/\swith\s+(.+?)\s*$/i)?.[1]?.trim() ?? null;
};

const getCleanLogText = (rawText) =>
  removeLogPlayerIds(rawText)
    // Strip terminal/control and bidirectional override characters from copied
    // game input while preserving intentional line breaks and tabs.
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F]/g, "")
    .replace(/[\u061C\u200E\u200F\u202A-\u202E\u2066-\u2069]/g, "")
    .replace(/\r\n?/g, "\n")
    .trim();

const PlayerName = ({ id, name, team, teamLabel }) => {
  const label = String(name ?? "").trim();
  const color =
    team === "Axis"
      ? "error.light"
      : team === "Allies"
      ? "info.light"
      : "text.primary";
  const accessibleLabel = teamLabel ? `${label} · ${teamLabel}` : label;
  if (!label) {
    return (
      <Typography component="span" variant="body2" color="text.secondary">
        –
      </Typography>
    );
  }

  if (!id) {
    return (
      <Tooltip title={teamLabel || ""} arrow disableHoverListener={!teamLabel}>
        <Typography
          component="span"
          variant="body2"
          fontWeight={700}
          color={color}
        >
          {label}
          {teamLabel ? (
            <Box
              component="span"
              sx={{
                border: 0,
                clip: "rect(0 0 0 0)",
                height: 1,
                margin: -1,
                overflow: "hidden",
                p: 0,
                position: "absolute",
                whiteSpace: "nowrap",
                width: 1,
              }}
            >
              {` · ${teamLabel}`}
            </Box>
          ) : null}
        </Typography>
      </Tooltip>
    );
  }

  return (
    <Tooltip title={teamLabel || ""} arrow disableHoverListener={!teamLabel}>
      <Box component="span" sx={{ display: "inline-flex" }}>
        <PlayerDrawerLink
          playerId={id}
          aria-label={accessibleLabel}
          sx={{ color, fontStyle: "normal", fontWeight: 700 }}
        >
          {label}
        </PlayerDrawerLink>
      </Box>
    </Tooltip>
  );
};

const getTeamLabel = (team, t) =>
  team === "Axis"
    ? t("views.team.axis")
    : team === "Allies"
    ? t("views.team.allies")
    : undefined;

const CombatEvent = ({ event, weapon, teams, t }) => (
  <Box
    sx={{
      minWidth: 0,
      maxWidth: "100%",
      overflowWrap: "anywhere",
      whiteSpace: "normal",
      wordBreak: "break-word",
    }}
  >
    <PlayerName
      id={event.player_id_1}
      name={event.player_name_1}
      team={teams[0]}
      teamLabel={getTeamLabel(teams[0], t)}
    />
    <Box
      component="span"
      aria-hidden="true"
      sx={{
        color: "text.secondary",
        display: "inline-block",
        mx: 0.5,
        verticalAlign: "text-bottom",
      }}
    >
      <FontAwesomeIcon icon={faArrowRight} fixedWidth />
    </Box>
    {weapon ? (
      <Tooltip title={weapon} arrow>
        <Box
          component="span"
          role="img"
          tabIndex={0}
          aria-label={weapon}
          sx={{
            color: "warning.main",
            display: "inline-grid",
            mx: 0.25,
            placeItems: "center",
            verticalAlign: "text-bottom",
          }}
        >
          <FontAwesomeIcon icon={faGun} fixedWidth />
        </Box>
      </Tooltip>
    ) : null}
    <PlayerName
      id={event.player_id_2}
      name={event.player_name_2}
      team={teams[1]}
      teamLabel={getTeamLabel(teams[1], t)}
    />
  </Box>
);

const ChatEvent = ({ event, team, t }) => {
  const playerName = String(event.player_name_1 ?? "").trim();
  let message = String(event.message ?? "").trim();

  if (playerName && message.startsWith(playerName)) {
    message = message.slice(playerName.length).replace(/^\s*:\s*/, "");
  }

  return (
    <Stack spacing={0.25} sx={{ minWidth: 0, maxWidth: "100%" }}>
      <Typography component="div" variant="body2" sx={{ lineHeight: 1.25 }}>
        <PlayerName
          id={event.player_id_1}
          name={playerName}
          team={team}
          teamLabel={getTeamLabel(team, t)}
        />
        :
      </Typography>
      <Typography
        component="div"
        variant="body2"
        sx={{
          minWidth: 0,
          maxWidth: "100%",
          overflowWrap: "anywhere",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        {message || "–"}
      </Typography>
    </Stack>
  );
};

function LogMessageStack({
  group,
  table,
  displaySettings,
  highlightedActions,
}) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const detailsId = useId();
  const count = group.rows.length;
  const body = getCleanLogText(group.body);
  const start = dayjs(group.start);
  const end = dayjs(group.end);
  const presentation = getLogPresentation(displaySettings);
  const highlighted = matchesLogActions("MESSAGE", highlightedActions);
  return (
    <Box
      component="li"
      role="listitem"
      data-testid="live-log-stack"
      data-highlighted={highlighted}
      sx={(theme) => ({
        borderBottom: `1px solid ${theme.palette.divider}`,
        borderLeft: `3px solid ${alpha(theme.palette.primary.main, 0.75)}`,
        bgcolor: alpha(theme.palette.primary.main, highlighted ? 0.16 : 0.035),
        boxShadow: highlighted
          ? `inset 0 0 0 1px ${theme.palette.primary.main}`
          : undefined,
        px: 1.25,
        py: presentation.paddingY,
      })}
    >
      <Stack direction="row" alignItems="flex-start" spacing={0.8}>
        <Typography
          component="time"
          dateTime={end.toISOString()}
          title={`${start.format("HH:mm:ss")} – ${end.format("HH:mm:ss")}`}
          variant="caption"
          sx={{ color: "text.secondary", flex: "0 0 42px", pt: 0.15 }}
        >
          {end.format("HH:mm")}
        </Typography>
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Typography variant="caption" color="primary.light">
            <FontAwesomeIcon icon={faCircleExclamation} fixedWidth />{" "}
            {t("actions.types.MESSAGE")}
          </Typography>
          <Typography
            variant="body2"
            sx={{
              mt: 0.5,
              overflowWrap: "anywhere",
              whiteSpace: "pre-wrap",
              unicodeBidi: "plaintext",
            }}
          >
            {body}
          </Typography>
          <Button
            size="small"
            aria-expanded={expanded}
            aria-controls={detailsId}
            onClick={() => setExpanded((value) => !value)}
            startIcon={
              <FontAwesomeIcon
                icon={expanded ? faChevronDown : faChevronRight}
                fixedWidth
              />
            }
            sx={{
              mt: 0.5,
              textTransform: "none",
              textAlign: "left",
              whiteSpace: "normal",
            }}
          >
            {t("views.live.repeatedMessages", { count })}
            {" · "}
            {t(
              expanded
                ? "views.live.hideLogDetails"
                : "views.live.showLogDetails"
            )}
          </Button>
        </Box>
      </Stack>
      <Box id={detailsId} hidden={!expanded} sx={{ mt: expanded ? 1 : 0 }}>
        {expanded ? (
          <>
            <Typography
              variant="caption"
              component="p"
              color="text.secondary"
              sx={{ mb: 0.5 }}
            >
              {t("views.live.scrollLogDetails", { count })}
            </Typography>
            <Box
              role="region"
              aria-label={t("views.live.repeatedMessages", { count })}
              tabIndex={0}
              data-testid="live-log-stack-scroll"
              sx={(theme) => ({
                maxHeight: "min(45vh, 360px)",
                overflowY: "auto",
                overflowX: "hidden",
                scrollbarGutter: "stable",
                scrollbarWidth: "thin",
                scrollbarColor: `${alpha(
                  theme.palette.primary.main,
                  0.52
                )} transparent`,
                "&:focus-visible": {
                  outline: `2px solid ${theme.palette.primary.main}`,
                  outlineOffset: -2,
                },
              })}
            >
              <CompactLogsList
                table={table}
                rows={group.rows}
                stackedDetail
                displaySettings={displaySettings}
                highlightedActions={highlightedActions}
              />
            </Box>
          </>
        ) : null}
      </Box>
    </Box>
  );
}

function CompactLogsList({
  table,
  rows,
  scrollable = false,
  stackedDetail = false,
  displaySettings,
  highlightedActions = [],
  onReadOlder,
  scrollReset,
}) {
  const { t } = useTranslation();
  const scrollRef = useRef(null);
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = 0;
  }, [scrollReset]);
  const presentation = getLogPresentation(displaySettings);
  const groups = useMemo(
    () =>
      stackedDetail
        ? rows.map((row) => ({ key: row.id, rows: [row] }))
        : groupLogRows(rows),
    [rows, stackedDetail]
  );
  const onlinePlayers = useGlobalStore(selectOnlinePlayerContexts);
  const playersById = useMemo(() => {
    const players = new Map();
    const remember = (id, details) => {
      const safeId = String(id ?? "").trim();
      if (!safeId) return;

      const previous = players.get(safeId) ?? {};
      players.set(safeId, {
        ...previous,
        ...Object.fromEntries(
          Object.entries(details).filter(
            ([, value]) => value !== null && value !== undefined && value !== ""
          )
        ),
      });
    };

    for (const player of onlinePlayers) {
      remember(player.player_id, {
        name: String(player.name ?? "").trim(),
        team: player.team,
        faction: player.faction,
      });
    }
    for (const event of table.options.data ?? []) {
      remember(event.player_id_1, {
        name: String(event.player_name_1 ?? "").trim(),
      });
      remember(event.player_id_2, {
        name: String(event.player_name_2 ?? "").trim(),
      });
    }
    return players;
  }, [onlinePlayers, table.options.data]);

  return (
    <Box
      component={stackedDetail ? "div" : "section"}
      ref={scrollRef}
      onScroll={(event) => {
        if (
          event.target === event.currentTarget &&
          event.currentTarget.scrollTop > 48
        )
          onReadOlder?.();
      }}
      role={stackedDetail ? undefined : "region"}
      aria-label={stackedDetail ? undefined : t("views.live.eventStream")}
      data-testid={
        stackedDetail ? "live-log-stack-details" : "live-event-stream"
      }
      tabIndex={scrollable ? 0 : undefined}
      sx={(theme) => ({
        minHeight: 0,
        outline: "none",
        position: "relative",
        "--log-font-size": presentation.fontSize,
        fontSize: "var(--log-font-size)",
        "& .MuiTypography-body2, & .MuiTypography-body1, & a": {
          fontSize: "var(--log-font-size)",
        },
        ...(scrollable
          ? {
              flex: "1 1 auto",
              overflowX: "hidden",
              overflowY: "auto",
              overscrollBehaviorY: "contain",
              scrollbarColor: `${alpha(
                theme.palette.primary.main,
                0.52
              )} transparent`,
              scrollbarGutter: "stable",
              scrollbarWidth: "thin",
              touchAction: "pan-y",
              WebkitOverflowScrolling: "touch",
              "&:hover, &:focus-visible": {
                boxShadow: `inset 0 0 0 1px ${alpha(
                  theme.palette.primary.main,
                  0.42
                )}`,
              },
            }
          : { overflow: "visible" }),
      })}
    >
      <Box component="ol" role="list" sx={{ listStyle: "none", m: 0, p: 0 }}>
        {groups.map((group) => {
          if (group.rows.length > 1) {
            return (
              <LogMessageStack
                key={group.key}
                group={group}
                table={table}
                displaySettings={displaySettings}
                highlightedActions={highlightedActions}
              />
            );
          }
          const row = group.rows[0];
          const event = row.original;
          const highlighted = matchesLogActions(
            event.action,
            highlightedActions
          );
          const rawText =
            typeof event.message === "string"
              ? event.message
              : String(event.message ?? "");
          const cleanText = getCleanLogText(rawText);
          const player1Context = playersById.get(
            String(event.player_id_1 ?? "")
          );
          const player2Context = playersById.get(
            String(event.player_id_2 ?? "")
          );
          const playerName1 =
            String(event.player_name_1 ?? "").trim() ||
            player1Context?.name ||
            "";
          const playerName2 =
            String(event.player_name_2 ?? "").trim() ||
            player2Context?.name ||
            "";
          const safeEvent = {
            ...event,
            action: String(event.action ?? ""),
            message: cleanText,
            player_name_1: playerName1,
            player_name_2: playerName2,
          };
          const eventTime = dayjs(event.timestamp_ms);
          const { label, labelKey, color, icon } = getEventMeta(
            safeEvent.action
          );
          const eventLabel = labelKey
            ? t(`views.live.${labelKey}`)
            : label || t("views.live.events");
          // Resolve both teams from the original event before the visible
          // message loses its `(Axis|Allies/player-id)` transport metadata.
          const playerTeams = getEventPlayerTeams(
            event,
            player1Context?.team,
            player2Context?.team
          );
          const isCombatEvent = ["KILL", "TEAM KILL"].includes(
            safeEvent.action
          );
          const isChatEvent = safeEvent.action.startsWith("CHAT");
          const weapon = getWeaponName(safeEvent, cleanText);
          return (
            <Box
              key={group.key}
              component="li"
              role="listitem"
              data-highlighted={highlighted}
              sx={(theme) => ({
                borderBottom: `1px solid ${theme.palette.divider}`,
                borderLeft: `3px solid ${alpha(
                  theme.palette[color].main,
                  0.75
                )}`,
                px: 1.25,
                py: presentation.paddingY,
                bgcolor: highlighted
                  ? alpha(theme.palette.primary.main, 0.16)
                  : undefined,
                boxShadow: highlighted
                  ? `inset 0 0 0 1px ${theme.palette.primary.main}`
                  : undefined,
                // A bounded detail list needs real row heights. Estimated
                // offscreen heights otherwise make End stop before entry 100.
                contentVisibility: stackedDetail ? "visible" : "auto",
                containIntrinsicSize: stackedDetail ? undefined : "0 88px",
                transition: "background-color 120ms ease",
                "&:hover": {
                  bgcolor: alpha(
                    theme.palette[highlighted ? "primary" : color].main,
                    highlighted ? 0.2 : 0.055
                  ),
                },
              })}
            >
              <Stack direction="row" alignItems="flex-start" spacing={0.8}>
                <Typography
                  component="time"
                  dateTime={
                    eventTime.isValid() ? eventTime.toISOString() : undefined
                  }
                  variant="caption"
                  sx={{
                    color: "text.secondary",
                    flex: stackedDetail ? "0 0 58px" : "0 0 42px",
                    pt: 0.15,
                  }}
                >
                  {eventTime.isValid()
                    ? eventTime.format(stackedDetail ? "HH:mm:ss" : "HH:mm")
                    : "--:--"}
                </Typography>
                <Box sx={{ minWidth: 0, flex: 1, maxWidth: "100%" }}>
                  <Stack
                    direction="row"
                    alignItems="center"
                    justifyContent="space-between"
                    gap={0.75}
                    sx={{ minWidth: 0, mb: 0.35 }}
                  >
                    <Stack
                      direction="row"
                      alignItems="center"
                      spacing={0.5}
                      sx={{ minWidth: 0 }}
                    >
                      <Box
                        component="span"
                        aria-hidden="true"
                        sx={{ color: `${color}.main`, fontSize: "0.85rem" }}
                      >
                        <FontAwesomeIcon icon={icon} fixedWidth />
                      </Box>
                      <Typography
                        variant="caption"
                        noWrap
                        sx={{ color: `${color}.light` }}
                      >
                        {eventLabel}
                      </Typography>
                    </Stack>
                    <CopyToClipboardButton
                      text={cleanText}
                      title={t("views.live.copyLog")}
                      iconOnly
                      disabled={!cleanText}
                      size="small"
                      aria-label={t("views.live.copyLog")}
                      copyIcon={<FontAwesomeIcon icon={faCopy} fixedWidth />}
                      copiedIcon={
                        <FontAwesomeIcon icon={faCheckDouble} fixedWidth />
                      }
                      sx={{
                        flex: "0 0 auto",
                        minWidth: { xs: 44, lg: 32 },
                        minHeight: { xs: 44, lg: 32 },
                        p: 0.5,
                        opacity: 0.72,
                        "&:hover, &:focus-visible": { opacity: 1 },
                        "& .MuiSvgIcon-root": { fontSize: "0.95rem" },
                      }}
                    />
                  </Stack>
                  <Box
                    sx={{
                      minWidth: 0,
                      maxWidth: "100%",
                      overflowWrap: "anywhere",
                      whiteSpace: "normal",
                      wordBreak: "break-word",
                      unicodeBidi: "plaintext",
                    }}
                  >
                    {isCombatEvent ? (
                      <CombatEvent
                        event={safeEvent}
                        weapon={weapon}
                        teams={playerTeams}
                        t={t}
                      />
                    ) : isChatEvent ? (
                      <ChatEvent
                        event={safeEvent}
                        team={playerTeams[0]}
                        t={t}
                      />
                    ) : safeEvent.action === "MESSAGE" ? (
                      <Stack spacing={0.25}>
                        {stackedDetail ? (
                          <Typography
                            component="div"
                            variant="caption"
                            color="text.secondary"
                          >
                            {t("views.live.messageRecipient")}{" "}
                            <PlayerName
                              id={event.player_id_1}
                              name={playerName1 || event.player_id_1}
                              team={playerTeams[0]}
                              teamLabel={getTeamLabel(playerTeams[0], t)}
                            />
                          </Typography>
                        ) : null}
                        <Typography
                          variant="body2"
                          sx={{ whiteSpace: "pre-wrap" }}
                        >
                          {getCleanLogText(getMessageBody(event)) || "–"}
                        </Typography>
                      </Stack>
                    ) : (
                      <Typography
                        component="div"
                        variant="body2"
                        sx={{ minWidth: 0, maxWidth: "100%" }}
                      >
                        {safeEvent.player_name_1 ? (
                          <LogMessage
                            log={{ ...safeEvent, team: playerTeams[0] }}
                            colored
                            wrap
                          />
                        ) : (
                          cleanText || "–"
                        )}
                      </Typography>
                    )}
                  </Box>
                </Box>
              </Stack>
            </Box>
          );
        })}
      </Box>
      {rows.length === 0 ? <NoRowsOverlay /> : null}
    </Box>
  );
}

export default memo(CompactLogsList);
