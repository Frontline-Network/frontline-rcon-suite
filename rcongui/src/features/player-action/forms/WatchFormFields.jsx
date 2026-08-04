import { ReasonField } from '../fields/ReasonField'
import { useTranslation } from "react-i18next";

export const WatchFormFields = (props) => {
  const { t } = useTranslation();
  return (
    <ReasonField helperText={t("fields.watchReasonHelp")} {...props} />
  )
};
