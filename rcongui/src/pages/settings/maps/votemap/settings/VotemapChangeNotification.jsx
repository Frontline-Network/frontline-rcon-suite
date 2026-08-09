import { Button } from "@mui/material";
import { useTranslation } from "react-i18next";

export function VotemapChangeNotification({ closeToast, data }) {
  const { t } = useTranslation();
  return (
    <div>
      <div>{t("maps.votemapConfigChanged")}</div>
      <ul>
        {data.changes.map((key) => (
          <li key={key}>{key}</li>
        ))}
      </ul>
      <Button
        size="small"
        color="primary"
        onClick={() => {
          if (data.onAccept) data.onAccept();
          closeToast("accept");
        }}
      >
        {t("common.confirm")}
      </Button>
      <Button
        size="small"
        color="secondary"
        onClick={() => closeToast("ignore")}
      >
        {t("maps.ignoreChanges")}
      </Button>
    </div>
  );
}
