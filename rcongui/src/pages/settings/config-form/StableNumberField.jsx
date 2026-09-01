import { useCallback, useEffect, useMemo, useState } from "react";
import { TextField } from "@mui/material";

const toDraft = (value) =>
  value === undefined || value === null ? "" : String(value);

const parseDraft = (draft, integer, min, max) => {
  const trimmed = draft.trim();
  if (!trimmed) return undefined;

  const parsed = Number(trimmed);
  if (!Number.isFinite(parsed)) return null;
  if (integer && !Number.isInteger(parsed)) return null;
  if (min !== undefined && parsed < Number(min)) return null;
  if (max !== undefined && parsed > Number(max)) return null;
  return parsed;
};

export const useStableNumberDraft = ({
  value,
  integer,
  min,
  max,
  requiredValue = false,
  onChange,
  onValidityChange,
}) => {
  const [draft, setDraft] = useState(() => toDraft(value));
  const [focused, setFocused] = useState(false);
  const invalid = useMemo(() => {
    const parsed = parseDraft(draft, integer, min, max);
    return parsed === null || (requiredValue && parsed === undefined);
  }, [draft, integer, max, min, requiredValue]);

  useEffect(() => {
    if (!focused) setDraft(toDraft(value));
  }, [focused, value]);

  useEffect(() => {
    onValidityChange?.(!invalid);
  }, [invalid, onValidityChange]);

  const commit = useCallback(
    (nextDraft) => {
      const parsed = parseDraft(nextDraft, integer, min, max);
      if (parsed !== null) onChange(parsed);
    },
    [integer, max, min, onChange]
  );

  const handleChange = useCallback(
    (event) => {
      const nextDraft = event.target.value;
      setDraft(nextDraft);

      // Keep empty and incomplete number strings local while the operator is
      // typing. Otherwise a controlled input restores the persisted value
      // between Backspace and the next digit.
      if (nextDraft.trim()) commit(nextDraft);
    },
    [commit]
  );

  const handleBlur = useCallback(() => {
    setFocused(false);
    commit(draft);
  }, [commit, draft]);

  return {
    draft,
    invalid,
    onBlur: handleBlur,
    onChange: handleChange,
    onFocus: () => setFocused(true),
  };
};

export default function StableNumberField({
  value,
  integer = true,
  requiredValue = false,
  invalidHelperText,
  onChange,
  onValidityChange,
  ...textFieldProps
}) {
  const htmlInputProps = textFieldProps.slotProps?.htmlInput;
  const draftProps = useStableNumberDraft({
    value,
    integer,
    min: htmlInputProps?.min,
    max: htmlInputProps?.max,
    requiredValue,
    onChange,
    onValidityChange,
  });

  return (
    <TextField
      {...textFieldProps}
      type="number"
      value={draftProps.draft}
      error={textFieldProps.error || draftProps.invalid}
      helperText={
        draftProps.invalid
          ? invalidHelperText ?? textFieldProps.helperText
          : textFieldProps.helperText
      }
      onFocus={draftProps.onFocus}
      onChange={draftProps.onChange}
      onBlur={draftProps.onBlur}
    />
  );
}
