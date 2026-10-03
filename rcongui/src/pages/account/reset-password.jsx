import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import RecoveryLayout from "./RecoveryLayout";
import PasswordForm from "./PasswordForm";

export default function ResetPassword() {
  const { uid } = useParams();
  const { t } = useTranslation();
  return (
    <RecoveryLayout
      wide
      title={t("accountPassword.resetTitle")}
      subtitle={t("accountPassword.resetSubtitle")}
    >
      <PasswordForm key={uid} mode="reset" uid={uid} />
    </RecoveryLayout>
  );
}
