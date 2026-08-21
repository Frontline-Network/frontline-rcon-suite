const LEGACY_CAPABILITIES = Object.freeze({
  read: true,
  set: true,
  remove: false,
});

/**
 * Interpret the server's declared sector-layout operations defensively.
 *
 * Installations older than the capability contract keep their established
 * read/set behaviour, while an explicit ``false`` is always honoured.  This
 * prevents a future game profile from exposing controls for an unsupported
 * RCON operation.
 */
export const resolveSectorLayoutCapabilities = (status = {}) => {
  const declared = status?.game_capabilities?.sector_layout;
  if (!declared || typeof declared !== "object") return { ...LEGACY_CAPABILITIES };

  return {
    read: declared.read !== false,
    set: declared.set !== false,
    remove: declared.remove === true,
  };
};

export { LEGACY_CAPABILITIES };
