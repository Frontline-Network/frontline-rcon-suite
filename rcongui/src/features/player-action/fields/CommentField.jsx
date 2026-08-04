import { ControlledTextInput } from "@/components/form/core/ControlledTextInput";
import { useTranslation } from "react-i18next";

export const CommentField = ({ control, errors, ...props }) => {
  const { t } = useTranslation();
  const error = errors['comment'];
  const hasError = !!error;

  return (
    <ControlledTextInput
      error={hasError}
      name={'comment'}
      label={t("fields.comment")}
      control={control}
      rules={{ minLength: { value: 5, message: t("fields.commentMin") }, ...props.rules }}
      helperText={hasError ? error.message : t("fields.commentHelp")}
      multiline
      minRows={5}
      fullWidth
      {...props}
    />
  );
};
