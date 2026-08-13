import AccountTreeIcon from "@mui/icons-material/AccountTree";
import GavelIcon from "@mui/icons-material/Gavel";
import { Alert, AlertTitle, Chip, Stack, Typography } from "@mui/material";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

const LinkedAccounts = ({ identity, compact = false }) => {
  const { t } = useTranslation();
  const accounts = identity?.linked_accounts ?? [];
  const restrictedAccounts = accounts.filter(
    (account) => account.is_banned || account.active_blacklists?.length
  );

  if (!accounts.length) return null;

  return (
    <Stack gap={0.75} sx={{ py: compact ? 0.5 : 1 }}>
      {restrictedAccounts.map((account) => (
        <Alert
          key={`restriction-${account.player_id}`}
          severity="error"
          icon={<GavelIcon />}
          variant="outlined"
        >
          <AlertTitle>{t("playerIdentity.restrictedTitle")}</AlertTitle>
          {t("playerIdentity.restrictedDescription", {
            game: t(`playerIdentity.games.${account.game}`),
            name: account.name,
          })}
          {account.active_blacklists?.map((record) => (
            <Typography key={record.id} variant="caption" display="block">
              {record.blacklist.name}: {record.reason}
            </Typography>
          ))}
        </Alert>
      ))}
      <Stack direction="row" alignItems="center" flexWrap="wrap" gap={0.75}>
        <Typography variant="caption" color="text.secondary">
          {t("playerIdentity.linkedAccounts")}
        </Typography>
        {accounts.map((account) => (
          <Chip
            key={account.player_id}
            component={Link}
            clickable
            to={`/records/players/${account.player_id}`}
            icon={account.is_banned || account.active_blacklists?.length ? <GavelIcon /> : <AccountTreeIcon />}
            label={`${t(`playerIdentity.games.${account.game}`)} · ${account.name}`}
            title={account.player_id}
            size="small"
            variant="outlined"
            color={account.is_banned || account.active_blacklists?.length ? "error" : "primary"}
          />
        ))}
      </Stack>
    </Stack>
  );
};

export default LinkedAccounts;
