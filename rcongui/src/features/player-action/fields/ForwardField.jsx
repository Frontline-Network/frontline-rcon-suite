import { ControlledCheckbox } from '@/components/form/core/ControlledCheckbox';
import { useTranslation } from "react-i18next";

export const ForwardField = ({ control, errors, ...props }) => {
  const { t } = useTranslation();
  return (
    <ControlledCheckbox
      checked={props.defaultValue}
      control={control}
      errors={errors}
      name={'forward'}
      label={t("fields.applyAllServers")}
      {...props}
    />
  );
};
