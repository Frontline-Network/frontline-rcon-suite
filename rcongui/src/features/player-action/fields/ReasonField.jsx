import { ControlledTextInput } from "@/components/form/core/ControlledTextInput";
import { MenuItem, Select } from "@mui/material";
import { useTemplates } from "@/hooks/useTemplates";
import { useState } from "react";
import { useTranslation } from "react-i18next";

export const ReasonField = ({ control, errors, setValue, helperText, ...props }) => {
  const { t } = useTranslation();
  const templates = useTemplates("reason");
  const [selectedTemplate, setSelectedTemplate] = useState("");
  const error = errors["reason"];
  const hasError = !!error;

  const handleOnSelectChange = (event) => {
    const value = event.target.value ?? "";
    if (value === "") {
      setSelectedTemplate(value);
    } else {
      const template = templates[value];
      setSelectedTemplate(String(value));
      setValue("reason", template.content, { shouldTouch: true });
    }
  };

  return (
    <>
      <ControlledTextInput
        error={hasError}
        name={"reason"}
        label={t("fields.reason")}
        control={control}
        rules={{ required: t("fields.reasonRequired") }}
        helperText={
          hasError ? error.message : (helperText ?? t("fields.messageHelp"))
        }
        multiline
        minRows={5}
        fullWidth
      />
      <Select
        id="saved-reasons-select"
        value={selectedTemplate}
        onChange={handleOnSelectChange}
        inputProps={{ "aria-label": t("fields.savedReasons") }}
        fullWidth
        displayEmpty
      >
        <MenuItem value="">
          <em>{t("fields.savedReasons")}</em>
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
