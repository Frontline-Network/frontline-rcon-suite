import { useRouteError } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { translateOperatorMessage } from "@/i18n/operator-messages";

export default function ErrorPage() {
  const { t } = useTranslation();
  const error = useRouteError();
  console.error(error);

  return (
    <div id="error-page">
      <h1>{t("sharedOperations.errorPageTitle")}</h1>
      <p>{t("sharedOperations.http.unexpectedError")}</p>
      <p>
        <i>{translateOperatorMessage(error.statusText || error.message || error.data, t)}</i>
      </p>
    </div>
  );
}
