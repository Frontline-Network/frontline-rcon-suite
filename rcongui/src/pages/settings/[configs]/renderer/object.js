import {InputLabel} from "@mui/material";
import { useTranslation } from "react-i18next";

const objectRenderer = (props) => {
  const { t } = useTranslation();
  const name = props.uischema.scope.replace('#/properties/', '');
  const label = props.label || props.schema?.title || name;

  return (
    <>
      <InputLabel>{label}</InputLabel>
      {t("settings.config.objectUnsupported", { name: label })}
    </>
  );
}

export const renderer = objectRenderer;
