import { rankWith } from "@jsonforms/core";
import { withJsonFormsControlProps } from "@jsonforms/react";
import PlayerFlagPicker from "@/pages/settings/config-form/PlayerFlagPicker";

const playerFlagScope = (uischema) => {
  if (uischema?.type !== "Control") return false;
  const scope = String(uischema.scope || "");
  return (
    scope.endsWith("/whitelist_flags") ||
    scope.endsWith("/flags") ||
    scope.endsWith("/whitelist_players/properties/has_flag") ||
    scope.endsWith("/has_flag")
  );
};

export const playerFlagsTester = rankWith(20, playerFlagScope);

const PlayerFlagsControl = ({
  data,
  enabled,
  handleChange,
  path,
  label,
  description,
  errors,
  visible,
}) => {
  if (!visible) return null;
  return (
    <PlayerFlagPicker
      value={Array.isArray(data) ? data : []}
      disabled={!enabled}
      label={label}
      help={description}
      error={errors}
      showNotice={false}
      onChange={(nextFlags) => handleChange(path, nextFlags)}
    />
  );
};

export const playerFlagsRenderer =
  withJsonFormsControlProps(PlayerFlagsControl);
