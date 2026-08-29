import { useCallback, useEffect, useState } from "react";
import { TextField } from "@mui/material";

const toDraft = (value) =>
  value === undefined || value === null ? "" : String(value);

const parseDraft = (draft, integer) => {
  const trimmed = draft.trim();
  if (!trimmed) return undefined;

  const parsed = Number(trimmed);
  if (!Number.isFinite(parsed)) return null;
  if (integer && !Number.isInteger(parsed)) return null;
  return parsed;
};

export const useStableNumberDraft = ({ value, integer, onChange }) => {
  const [draft, setDraft] = useState(() => toDraft(value));
  const [focused, setFocused] = useState(false);

  useEffect(() => {
    if (!focused) setDraft(toDraft(value));
  }, [focused, value]);

  const commit = useCallback(
    (nextDraft) => {
      const parsed = parseDraft(nextDraft, integer);
      if (parsed !== null) onChange(parsed);
    },
    [integer, onChange]
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
    onBlur: handleBlur,
    onChange: handleChange,
    onFocus: () => setFocused(true),
  };
};

export default function StableNumberField({
  value,
  integer = true,
  onChange,
  ...textFieldProps
}) {
  const draftProps = useStableNumberDraft({ value, integer, onChange });

  return (
    <TextField
      {...textFieldProps}
      type="number"
      value={draftProps.draft}
      onFocus={draftProps.onFocus}
      onChange={draftProps.onChange}
      onBlur={draftProps.onBlur}
    />
  );
}
