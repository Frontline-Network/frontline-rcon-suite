import {InputLabel} from "@mui/material";
import { useTranslation } from "react-i18next";

const objectRenderer = (props) => {
  const { t } = useTranslation();
  const name = props.uischema.scope.replace('#/properties/', '');

  return (
    <>
      <InputLabel>{name}</InputLabel>
      {t("settings.config.objectUnsupported", { name })}
    </>
  );
}

export const renderer = objectRenderer;
