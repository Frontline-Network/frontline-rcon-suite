import dayjs from 'dayjs';
import { ControlledDesktopDateTimePicker } from '@/components/form/core/ControlledDesktopDateTimePicker';
import { useTranslation } from "react-i18next";

export const ExpirationField = ({ control, errors, defaultValue, name }) => {
  const { t } = useTranslation();
  const error = errors['expiration'];
  const hasError = !!error;

  if (hasError && error.type === 'moreThanNow') {
    error.message = t("fields.expirationFuture");
  }

  return (
    <ControlledDesktopDateTimePicker
      defaultValue={defaultValue ?? dayjs()}
      control={control}
      errors={errors}
      name={name ?? "expiration"}
      rules={{ required: t("fields.expirationRequired"), moreThanNow: t("fields.expirationFuture"), valueAsDate: true, validate: {
        moreThanNow: (value) => dayjs().isBefore(value),
      } }}
      error={error}
      disablePast
      maxDate={dayjs("3000-01-01T00:00:00+00:00")}
      slotProps={{
        textField: {
          helperText: hasError
            ? error.message
            : t("fields.expirationHelp"),
        },
      }}
    />
  );
};
