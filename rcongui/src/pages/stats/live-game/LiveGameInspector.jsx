import {
  Box,
  Button,
  Divider,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import PersonOutlineIcon from "@mui/icons-material/PersonOutline";
import PublicIcon from "@mui/icons-material/Public";
import { ActionMenuButton } from "@/features/player-action/ActionMenu";
import { generatePlayerActions } from "@/features/player-action/actions";
import { usePlayerSidebar } from "@/hooks/usePlayerSidebar";
import { getColoredFactionIconSrc } from "@/utils/lib";
import {
  formatMatchDuration,
  getTopEntries,
} from "./live-game-utils";

const Label = ({ children }) => (
  <Typography
    component="span"
    sx={{
      display: "block",
      color: "text.secondary",
      fontSize: "0.64rem",
      fontWeight: 700,
      letterSpacing: "0.09em",
      lineHeight: 1.2,
      textTransform: "uppercase",
    }}
  >
    {children}
  </Typography>
);

const Metric = ({ label, value, tone }) => (
  <Box sx={{ minWidth: 0, px: 0.9, py: 0.85, borderRight: "1px solid", borderBottom: "1px solid", borderColor: "divider" }}>
    <Label>{label}</Label>
    <Typography
      sx={{
        mt: 0.3,
        color: tone ?? "text.primary",
        fontSize: "0.88rem",
        fontWeight: 600,
        fontVariantNumeric: "tabular-nums",
      }}
    >
      {value}
    </Typography>
  </Box>
);

const DetailList = ({ label, entries, emptyLabel }) => (
  <Box sx={{ minWidth: 0 }}>
    <Label>{label}</Label>
    <Stack spacing={0.45} sx={{ mt: 0.7 }}>
      {entries.length ? (
        entries.map((entry) => (
          <Stack key={entry.key} direction="row" justifyContent="space-between" gap={1}>
            <Typography
              sx={{
                minWidth: 0,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
                color: "text.secondary",
                fontSize: "0.7rem",
              }}
            >
              {entry.label}
            </Typography>
            <Typography sx={{ fontSize: "0.7rem", fontVariantNumeric: "tabular-nums" }}>
              {entry.count}
            </Typography>
          </Stack>
        ))
      ) : (
        <Typography sx={{ color: "text.disabled", fontSize: "0.7rem" }}>{emptyLabel}</Typography>
      )}
    </Stack>
  </Box>
);

export default function LiveGameInspector({ player, playerNames, t, compact = false }) {
  const { openWithId } = usePlayerSidebar();

  if (!player) {
    return (
      <Stack
        alignItems="center"
        justifyContent="center"
        sx={{ minHeight: compact ? 240 : 540, px: 3, border: "1px solid", borderColor: "divider", bgcolor: "background.paper" }}
      >
        <PersonOutlineIcon sx={{ mb: 1.25, color: "text.disabled", fontSize: 32 }} />
        <Typography sx={{ textAlign: "center", color: "text.secondary", fontSize: "0.78rem" }}>
          {t("stats.liveGame.selectPlayerHint")}
        </Typography>
      </Stack>
    );
  }

  const recipient = { name: player.player, player_id: player.player_id };
  const teamLabel = player.team === "allies" ? t("views.team.allies") : player.team === "axis" ? t("views.team.axis") : t("stats.liveGame.unknownTeam");
  const statusLabel = player.status === "online" ? t("stats.liveGame.statusOnline") : player.status === "idle" ? t("stats.liveGame.statusIdle") : player.status === "offline" ? t("stats.liveGame.statusOffline") : t("stats.liveGame.statusUnknown");
  const opponents = getTopEntries(player.most_killed, playerNames);
  const nemeses = getTopEntries(player.death_by, playerNames);
  const weapons = getTopEntries(player.weapons, null, 4);
  const country = player.steaminfo?.country;

  return (
    <Box
      sx={{
        minWidth: 0,
        height: compact ? "auto" : "100%",
        border: "1px solid",
        borderLeft: "2px solid",
        borderColor: "divider",
        borderLeftColor: "primary.main",
        bgcolor: "background.paper",
      }}
    >
      <Stack direction="row" alignItems="center" gap={1} sx={{ p: 1.25 }}>
        <Box component="img" src={getColoredFactionIconSrc(player.faction ?? player.team)} alt="" width={26} height={26} sx={{ objectFit: "contain" }} />
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Typography
            component="h2"
            sx={{
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              fontSize: "0.9rem",
              fontWeight: 700,
            }}
          >
            {player.player}
          </Typography>
          <Stack direction="row" alignItems="center" gap={0.55} sx={{ mt: 0.15 }}>
            <Box component="span" sx={{ width: 6, height: 6, bgcolor: player.status === "online" ? "success.main" : player.status === "idle" ? "warning.main" : "text.disabled" }} />
            <Typography sx={{ color: "text.secondary", fontSize: "0.65rem" }}>
              {teamLabel} · {statusLabel}
            </Typography>
          </Stack>
        </Box>
        <Tooltip title={t("stats.liveGame.profile")}>
          <IconButton onClick={() => openWithId(player.player_id)} size="small" sx={{ border: "1px solid", borderColor: "divider", borderRadius: 0 }}>
            <PersonOutlineIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Stack>

      <Divider />

      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", "& > :nth-of-type(3n)": { borderRight: 0 }, "& > :nth-last-of-type(-n+3)": { borderBottom: 0 } }}>
        <Metric label={t("stats.gameDetails.metrics.kills")} value={player.kills} />
        <Metric label={t("stats.gameDetails.deaths")} value={player.deaths} />
        <Metric label="K/D" value={player.kill_death_ratio.toFixed(2)} tone={player.kill_death_ratio >= 2 ? "success.main" : undefined} />
        <Metric label={t("stats.liveGame.kpmShort")} value={player.kills_per_minute.toFixed(2)} />
        <Metric label="TK" value={player.teamkills} tone={player.teamkills > 0 ? "warning.main" : undefined} />
        <Metric label={t("stats.liveGame.timeShort")} value={formatMatchDuration(player.time_seconds)} />
      </Box>

      <Divider />

      <Box sx={{ px: 1.25, py: 1.1 }}>
        <Label>{t("stats.liveGame.performance")}</Label>
        <Box sx={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", mt: 0.75, border: "1px solid", borderColor: "divider", "& > :nth-of-type(4n)": { borderRight: 0 }, "& > *": { borderBottom: 0 } }}>
          <Metric label={t("stats.gameDetails.metrics.combat")} value={player.combat} />
          <Metric label={t("stats.gameDetails.metrics.offense")} value={player.offense} />
          <Metric label={t("stats.gameDetails.metrics.defense")} value={player.defense} />
          <Metric label={t("stats.liveGame.supportShort")} value={player.support} />
        </Box>
      </Box>

      <Divider />

      <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1.5, px: 1.25, py: 1.1 }}>
        <DetailList label={t("stats.liveGame.mostKilled")} entries={opponents} emptyLabel={t("stats.liveGame.noDetailData")} />
        <DetailList label={t("stats.liveGame.nemesis")} entries={nemeses} emptyLabel={t("stats.liveGame.noDetailData")} />
        <Box sx={{ gridColumn: "1 / -1" }}>
          <DetailList label={t("stats.liveGame.weapons")} entries={weapons} emptyLabel={t("stats.liveGame.noDetailData")} />
        </Box>
      </Box>

      <Divider />

      <Box sx={{ px: 1.25, py: 1.1 }}>
        <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 1.25 }}>
          <Box>
            <Label>{t("stats.liveGame.level")}</Label>
            <Typography sx={{ mt: 0.25, fontSize: "0.75rem" }}>{player.level || "–"}</Typography>
          </Box>
          <Box>
            <Label>{t("stats.liveGame.country")}</Label>
            <Stack direction="row" alignItems="center" gap={0.55} sx={{ mt: 0.25 }}>
              {country && country !== "private" && <PublicIcon sx={{ color: "text.secondary", fontSize: 14 }} />}
              <Typography sx={{ fontSize: "0.75rem" }}>{country && country !== "private" ? country : "–"}</Typography>
            </Stack>
          </Box>
          <Box sx={{ gridColumn: "1 / -1" }}>
            <Label>{t("stats.liveGame.playerId")}</Label>
            <Stack direction="row" alignItems="center" gap={0.35} sx={{ mt: 0.2 }}>
              <Typography sx={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "text.secondary", fontSize: "0.7rem" }}>
                {player.player_id}
              </Typography>
              <Tooltip title={t("stats.liveGame.copyPlayerId")}>
                <IconButton size="small" onClick={() => navigator.clipboard?.writeText(player.player_id)} sx={{ p: 0.25, borderRadius: 0 }}>
                  <ContentCopyIcon sx={{ fontSize: 14 }} />
                </IconButton>
              </Tooltip>
            </Stack>
          </Box>
        </Box>
      </Box>

      <Divider />

      <Stack direction="row" gap={0.65} sx={{ p: 1.1 }}>
        <Button startIcon={<PersonOutlineIcon />} onClick={() => openWithId(player.player_id)} sx={{ flex: 1, minHeight: 40, border: "1px solid", borderColor: "divider", borderRadius: 0 }}>
          {t("stats.liveGame.profile")}
        </Button>
        <ActionMenuButton
          actions={generatePlayerActions({ onlineAction: false })}
          recipients={recipient}
          renderButton={(props) => (
            <Button {...props} startIcon={<MoreHorizIcon />} sx={{ flex: 1, minHeight: 40, border: "1px solid", borderColor: "divider", borderRadius: 0 }}>
              {t("stats.liveGame.actions")}
            </Button>
          )}
        />
      </Stack>
    </Box>
  );
}
