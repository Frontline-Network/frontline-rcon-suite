import { Box } from "@mui/material";
import { useTranslation } from "react-i18next";
import PageHeader from "@/components/shared/PageHeader";
import PasswordForm from "./PasswordForm";

export default function AccountPassword() {
  const { t } = useTranslation();
  return (
    <Box sx={{ minWidth: 0, maxWidth: 1120 }}>
      <PageHeader
        title={t("sidebar.changePassword")}
        subtitle={t("accountPassword.subtitle")}
      />
      <PasswordForm />
    </Box>
  );
}
