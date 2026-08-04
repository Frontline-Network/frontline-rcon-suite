export const getMapModeLabel = (t, mode) =>
  t(`views.team.gameModes.${mode}`, { defaultValue: mode });

export const getMapEnvironmentLabel = (t, environment) =>
  t(`maps.environments.${environment}`, { defaultValue: environment });
