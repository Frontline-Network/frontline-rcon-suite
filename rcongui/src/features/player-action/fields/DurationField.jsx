import { ControlledTextInput } from '@/components/form/core/ControlledTextInput';
import { useTranslation } from "react-i18next";

export const DurationField = ({ control, errors, ...props }) => {
  const { t } = useTranslation();
  const error = errors['duration'];
  const hasError = !!error;

  return (
    <ControlledTextInput
      defaultValue={2}
      type={'number'}
      error={hasError}
      name={'duration_hours'}
      label={t("fields.duration")}
      control={control}
      rules={{ required: t("fields.durationRequired"), valueAsNumber: true, min: { value: 1, message: t("fields.durationMin") } }}
      helperText={hasError ? error.message : t("fields.durationHelp")}
      fullWidth
      {...props}
    />
  );
};
