import { memo } from "react";
import { isIntegerControl, isNumberControl, rankWith } from "@jsonforms/core";
import { withJsonFormsControlProps } from "@jsonforms/react";
import {
  MaterialInputControl,
  useInputComponent,
} from "@jsonforms/material-renderers";
import { useStableNumberDraft } from "./StableNumberField";

const StableNumericInput = memo(function StableNumericInput(props) {
  const {
    className,
    data,
    enabled,
    handleChange,
    id,
    isValid,
    label,
    path,
    schema,
    uischema,
  } = props;
  const InputComponent = useInputComponent();
  const integer = schema?.type === "integer";
  const draftProps = useStableNumberDraft({
    value: data,
    integer,
    onChange: (value) => handleChange(path, value),
  });

  return (
    <InputComponent
      type="number"
      label={label}
      value={draftProps.draft}
      onFocus={draftProps.onFocus}
      onChange={draftProps.onChange}
      onBlur={draftProps.onBlur}
      className={className}
      id={id}
      disabled={!enabled}
      autoFocus={uischema?.options?.focus}
      inputProps={{
        min: schema?.minimum,
        max: schema?.maximum,
        step: integer ? 1 : schema?.multipleOf || "any",
      }}
      fullWidth
      error={!isValid}
    />
  );
});

const StableNumericControl = (props) => (
  <MaterialInputControl {...props} input={StableNumericInput} />
);

export const stableIntegerControlTester = rankWith(3, isIntegerControl);
export const stableNumberControlTester = rankWith(3, isNumberControl);

export const stableNumericControlRenderer =
  withJsonFormsControlProps(StableNumericControl);
