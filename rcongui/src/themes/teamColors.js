const normalizeTeam = (team) =>
  String(team || "")
    .trim()
    .toLowerCase();

export const getThemeTeamTone = (theme, team) => {
  const normalized = normalizeTeam(team);

  if (normalized === "axis" || normalized === "achsenmächte") {
    return theme.palette.error;
  }

  if (normalized === "allies" || normalized === "alliierte") {
    return theme.palette.info;
  }

  const neutral = theme.palette.text.secondary;
  return { light: neutral, main: neutral, dark: neutral };
};

export const getThemeTeamColor = (theme, team) =>
  getThemeTeamTone(theme, team).main;

export const getThemeTeamColors = (theme) => ({
  allies: getThemeTeamColor(theme, "allies"),
  axis: getThemeTeamColor(theme, "axis"),
});
