import { ControlledTextInput } from "@/components/form/core/ControlledTextInput";
import { useTemplates } from "@/hooks/useTemplates";
import { MenuItem, Select } from "@mui/material";
import { useState } from "react";
import { useTranslation } from "react-i18next";

export const MessageField = ({ control, errors, setValue, ...props }) => {
  const { t } = useTranslation();
  const templates = useTemplates("message");
  const [selectedTemplate, setSelectedTemplate] = useState("");
  const error = errors["message"];
  const hasError = !!error;

  const handleOnSelectChange = (event) => {
    const value = event.target.value ?? '';
    if (value === '') {
      setSelectedTemplate(value)
    } else {
      const template = templates[value]
      setSelectedTemplate(String(value))
      setValue('message', template.content, { shouldTouch: true })
    }
  }

  return (
    <>
      <ControlledTextInput
        error={hasError}
        name={"message"}
        label={t("fields.message")}
        control={control}
        rules={{ required: t("fields.messageRequired") }}
        helperText={
          hasError ? error.message : t("fields.messageHelp")
        }
        multiline
        minRows={5}
        fullWidth
      />
      <Select
        id="saved-messages-select"
        value={selectedTemplate}
        onChange={handleOnSelectChange}
        inputProps={{ "aria-label": t("fields.savedMessages") }}
        fullWidth
        displayEmpty
      >
        <MenuItem value="">
          <em>{t("fields.savedMessages")}</em>
        </MenuItem>
        {templates.map((template, i) => {
          return (
            <MenuItem key={template.id} value={String(i)}>
              {template.title}
            </MenuItem>
          );
        })}
      </Select>
    </>
  );
};
