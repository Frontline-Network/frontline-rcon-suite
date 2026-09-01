export const FRONTLINE_GEOMETRY = Object.freeze({
  radius: Object.freeze({
    structure: 0,
    control: 2,
    overlay: 4,
    round: 999,
  }),
  focusRing: Object.freeze({
    width: 2,
    offset: 2,
  }),
});

export const frontlineFocusRing = (color) =>
  `${FRONTLINE_GEOMETRY.focusRing.width}px solid ${color}`;
