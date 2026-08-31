import AccountTreeIcon from "@mui/icons-material/AccountTree";
import GavelIcon from "@mui/icons-material/Gavel";
import { Alert, AlertTitle, Chip, Stack, Typography } from "@mui/material";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { normalizeGame } from "@/utils/game-context";

const isSteamId = (playerId) => /^\d{17}$/.test(String(playerId ?? ""));

const getPlayerName = (player) =>
  player?.account?.name ??
  player?.names?.[0]?.name ??
  player?.soldier?.name ??
  player?.name ??
  "???";

const getCurrentGame = (player) =>
  normalizeGame(
    player?.game ?? player?.account?.game ?? player?.soldier?.game
  ) ?? (isSteamId(player?.player_id) ? "hll" : "hllv");

const normalizeAccount = (account) => ({
  ...account,
  game: normalizeGame(account?.game) ?? account?.game,
});

const LinkedAccounts = ({
  player,
  identity = player?.identity,
  compact = false,
  interactive = true,
  showLabel = true,
  showWarnings = true,
}) => {
  const { t } = useTranslation();
  const linkedAccounts = Array.isArray(identity?.linked_accounts)
    ? identity.linked_accounts.map(normalizeAccount)
    : [];
  const restrictedAccounts = linkedAccounts.filter(
    (account) => account.is_banned || account.active_blacklists?.length
  );

  if (!linkedAccounts.length) return null;

  const currentAccount = player?.player_id
    ? {
        player_id: player.player_id,
        steam_id: player.steam_id,
        name: getPlayerName(player),
        game: getCurrentGame(player),
        is_current: true,
      }
    : null;
  const accounts = [currentAccount, ...linkedAccounts]
    .filter(Boolean)
    .filter(
      (account, index, allAccounts) =>
        allAccounts.findIndex(
          (candidate) => candidate.player_id === account.player_id
        ) === index
    );

  return (
    <Stack gap={0.75} sx={{ py: compact ? 0.25 : 1 }}>
      {showWarnings &&
        restrictedAccounts.map((account) => (
          <Alert
            key={`restriction-${account.player_id}`}
            severity="error"
            icon={<GavelIcon />}
            variant="outlined"
          >
            <AlertTitle>{t("playerIdentity.restrictedTitle")}</AlertTitle>
            {t("playerIdentity.restrictedDescription", {
              game: t(`playerIdentity.games.${account.game}`, {
                defaultValue: account.game,
              }),
              name: account.name,
            })}
            {account.active_blacklists?.map((record) => (
              <Typography key={record.id} variant="caption" display="block">
                {record.blacklist.name}: {record.reason}
              </Typography>
            ))}
          </Alert>
        ))}
      <Stack
        direction="row"
        alignItems="center"
        flexWrap="wrap"
        gap={compact ? 0.5 : 0.75}
      >
        {showLabel ? (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{
              fontSize: compact ? "0.625rem" : undefined,
              fontWeight: 700,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
            }}
          >
            {t("playerIdentity.linkedAccounts")}
          </Typography>
        ) : null}
        {accounts.map((account) => (
          <Chip
            key={account.player_id}
            {...(!account.is_current && interactive
              ? {
                  component: Link,
                  clickable: true,
                  to: `/records/players/${account.player_id}`,
                }
              : {})}
            icon={
              account.is_banned || account.active_blacklists?.length ? (
                <GavelIcon />
              ) : (
                <AccountTreeIcon />
              )
            }
            label={`${t(`playerIdentity.gameCodes.${account.game}`, {
              defaultValue: String(account.game ?? "?").toUpperCase(),
            })} · ${account.name}${
              account.is_current
                ? ` · ${t("playerIdentity.currentAccount")}`
                : ""
            }`}
            title={account.player_id}
            size="small"
            variant={account.is_current ? "filled" : "outlined"}
            color={
              account.is_banned || account.active_blacklists?.length
                ? "error"
                : "primary"
            }
            sx={{
              borderRadius: 0,
              height: compact ? 24 : 28,
              maxWidth: "100%",
              "& .MuiChip-label": {
                overflow: "hidden",
                px: compact ? 0.75 : 1,
                textOverflow: "ellipsis",
              },
            }}
          />
        ))}
      </Stack>
    </Stack>
  );
};

export default LinkedAccounts;
