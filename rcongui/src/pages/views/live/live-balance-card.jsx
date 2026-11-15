import { Alert, Button } from "@mui/material";
import { useTranslation } from "react-i18next";
import AutobalancerCard from "../team/autobalancer-card";

export function LiveBalanceCard({ teams, gameState, settings }) {
  const { t } = useTranslation();
  const { userName, preferences, query, mutation } = settings;
  const ready = Boolean(userName && query.isSuccess);
  const saveFailed =
    mutation.isError &&
    mutation.variables?.source === "balance" &&
    mutation.variables?.owner === userName;

  return (
    <AutobalancerCard
      key={userName}
      teams={teams}
      gameState={gameState}
      detailsExpanded={preferences.balance_expanded}
      detailsDisabled={!ready || mutation.isPending}
      onDetailsExpandedChange={(expanded) => {
        if (!ready || mutation.isPending) return;
        mutation.mutate({
          owner: userName,
          source: "balance",
          preferences: { ...preferences, balance_expanded: expanded },
        });
      }}
      detailsFeedback={
        query.isError ? (
          <Alert
            severity="error"
            action={
              <Button onClick={() => query.refetch()}>
                {t("views.live.retrySettings")}
              </Button>
            }
          >
            {t("views.live.loadSettingsFailed")}
          </Alert>
        ) : saveFailed ? (
          <Alert severity="error">{t("views.live.saveSettingsFailed")}</Alert>
        ) : null
      }
    />
  );
}
