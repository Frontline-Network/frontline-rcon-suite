export function zoomCamera(camera, factor, anchor = { x: 0.5, y: 0.5 }) {
  const scale = Math.max(1, Math.min(8, camera.scale * factor));
  return {
    scale,
    x: anchor.x - ((anchor.x - camera.x) * scale) / camera.scale,
    y: anchor.y - ((anchor.y - camera.y) * scale) / camera.scale,
  };
}

export function wheelZoomFactor(delta, mode = 0, pageHeight = 800) {
  const pixels = delta * (mode === 1 ? 16 : mode === 2 ? pageHeight : 1);
  return Math.exp(-Math.max(-600, Math.min(600, pixels)) * 0.002);
}

// The root SVG matrix includes its letterboxing, CSS sizing and page scroll.
// Use root coordinates, never the transformed player/camera group's matrix.
export function pointerOnMap(svg, clientX, clientY) {
  const matrix = svg?.getScreenCTM();
  if (!matrix) return null;
  const point = svg.createSVGPoint();
  point.x = clientX;
  point.y = clientY;
  const local = point.matrixTransform(matrix.inverse());
  return { x: local.x / 1000, y: local.y / 1000 };
}
