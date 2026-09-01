import { useTranslation } from "react-i18next";
import PageState from "@/components/shared/PageState";

export function NoRowsOverlay() {
  const { t } = useTranslation();

  return <PageState compact kind="empty" title={t("common.noData")} />;
}
