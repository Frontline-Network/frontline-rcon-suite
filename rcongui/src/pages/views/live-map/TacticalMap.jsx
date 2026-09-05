import { useEffect, useRef, useState } from "react";
import { Box, Button, Stack, Typography, useTheme } from "@mui/material";
import { getThemeTeamColor } from "@/themes/teamColors";
import { getTacticalMapImageSrc } from "@/utils/map-images.mjs";
import { projectionReady } from "./geometry.mjs";
import { pointerOnMap, wheelZoomFactor, zoomCamera } from "./interaction.mjs";

export default function TacticalMap({
  frame,
  players,
  selected,
  following,
  onSelect,
  onManualNavigate,
  trails,
  showPlayers,
  encounter,
  t,
}) {
  const theme = useTheme();
  const [camera, setCamera] = useState({ x: 0, y: 0, scale: 1 });
  const [isDragging, setIsDragging] = useState(false);
  const drag = useRef(null);
  const svg = useRef(null);
  const mapId = frame?.map?.id;
  useEffect(() => {
    drag.current = null;
    setIsDragging(false);
    setCamera({ x: 0, y: 0, scale: 1 });
  }, [mapId]);
  useEffect(() => {
    const element = svg.current;
    const onWheel = (event) => {
      const anchor = pointerOnMap(element, event.clientX, event.clientY);
      if (!anchor || !event.deltaY) return;
      event.preventDefault();
      onManualNavigate();
      setCamera((c) =>
        zoomCamera(
          c,
          wheelZoomFactor(event.deltaY, event.deltaMode, element.clientHeight),
          anchor
        )
      );
    };
    // React's delegated wheel handler can be passive. This listener must be
    // non-passive so zooming the map never also scrolls the page underneath it.
    element.addEventListener("wheel", onWheel, { passive: false });
    return () => element.removeEventListener("wheel", onWheel);
  }, [onManualNavigate]);
  const target = players.find((p) => p.player_id === selected)?.map_position;
  useEffect(() => {
    if (following && target)
      setCamera((c) => ({
        ...c,
        x: 0.5 - target.x * c.scale,
        y: 0.5 - target.y * c.scale,
      }));
  }, [following, target?.x, target?.y]);
  const calibrated = projectionReady(frame?.calibration);
  const encounterPoint =
    calibrated && encounter?.round_id === frame?.round_id
      ? encounter.map_position
      : null;
  const image = getTacticalMapImageSrc(frame?.map);
  const zoom = (factor) => {
    onManualNavigate();
    setCamera((c) => zoomCamera(c, factor));
  };
  const onDown = (e) => {
    if (!e.isPrimary || ![0, 1].includes(e.button) || drag.current) return;
    const point = pointerOnMap(svg.current, e.clientX, e.clientY);
    if (!point) return;
    drag.current = {
      id: e.pointerId,
      button: e.button,
      startX: e.clientX,
      startY: e.clientY,
      point,
      moved: false,
      playerId: e.target.closest("[data-player-id]")?.dataset.playerId,
    };
    setIsDragging(true);
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const onMove = (e) => {
    const gesture = drag.current;
    if (!gesture || gesture.id !== e.pointerId) return;
    if (
      !gesture.moved &&
      Math.hypot(e.clientX - gesture.startX, e.clientY - gesture.startY) < 4
    )
      return;
    const point = pointerOnMap(svg.current, e.clientX, e.clientY);
    if (!point) return;
    if (!gesture.moved) onManualNavigate();
    gesture.moved = true;
    const dx = point.x - gesture.point.x,
      dy = point.y - gesture.point.y;
    gesture.point = point;
    setCamera((c) => ({ ...c, x: c.x + dx, y: c.y + dy }));
  };
  const endGesture = (e, cancelled = false) => {
    const gesture = drag.current;
    if (!gesture || gesture.id !== e.pointerId) return;
    drag.current = null;
    setIsDragging(false);
    if (e.currentTarget.hasPointerCapture(e.pointerId))
      e.currentTarget.releasePointerCapture(e.pointerId);
    if (
      !cancelled &&
      !gesture.moved &&
      gesture.button === 0 &&
      gesture.playerId
    )
      onSelect(gesture.playerId);
  };
  return (
    <Box
      sx={{
        position: "relative",
        border: 1,
        borderColor: "divider",
        bgcolor: "background.default",
        overflow: "hidden",
      }}
    >
      <Stack
        direction="row"
        spacing={1}
        sx={{ p: 1, borderBottom: 1, borderColor: "divider" }}
      >
        <Button size="small" onClick={() => zoom(1.5)} aria-label={t("zoomIn")}>
          +
        </Button>
        <Button
          size="small"
          onClick={() => zoom(1 / 1.5)}
          aria-label={t("zoomOut")}
        >
          −
        </Button>
        <Button
          size="small"
          onClick={() => {
            onManualNavigate();
            setCamera({ x: 0, y: 0, scale: 1 });
          }}
        >
          {t("resetView")}
        </Button>
        <Typography
          sx={{ ml: "auto !important", alignSelf: "center" }}
          variant="caption"
        >
          {Math.round(camera.scale * 100)} %
        </Typography>
      </Stack>
      <svg
        ref={svg}
        viewBox="0 0 1000 1000"
        role="group"
        aria-label={t("mapLabel")}
        style={{
          display: "block",
          width: "100%",
          maxHeight: "72vh",
          touchAction: "none",
          userSelect: "none",
          cursor: isDragging ? "grabbing" : "grab",
        }}
        onDragStart={(e) => e.preventDefault()}
        onPointerDown={onDown}
        onPointerMove={onMove}
        onPointerUp={(e) => endGesture(e)}
        onPointerCancel={(e) => endGesture(e, true)}
        onLostPointerCapture={(e) => endGesture(e, true)}
      >
        <g
          data-testid="map-camera"
          transform={`translate(${camera.x * 1000} ${camera.y * 1000}) scale(${
            camera.scale
          })`}
        >
          {image && (
            <image
              href={image}
              width="1000"
              height="1000"
              preserveAspectRatio="none"
            />
          )}
          {calibrated &&
            trails.map((line, i) => (
              <polyline
                key={i}
                points={line
                  .map((p) => `${p.x * 1000},${p.y * 1000}`)
                  .join(" ")}
                fill="none"
                stroke={theme.palette.primary.main}
                strokeWidth={3 / camera.scale}
                strokeDasharray={`${8 / camera.scale} ${4 / camera.scale}`}
              />
            ))}
          {encounterPoint && (
            <g
              data-testid="encounter-marker"
              transform={`translate(${encounterPoint.x * 1000} ${
                encounterPoint.y * 1000
              })`}
            >
              <circle
                r={18 / camera.scale}
                fill="none"
                stroke={theme.palette.warning.main}
                strokeWidth={3 / camera.scale}
              />
              <text
                x={22 / camera.scale}
                y={0}
                fontSize={13 / camera.scale}
                fill={theme.palette.common.white}
                stroke={theme.palette.common.black}
                strokeWidth={3 / camera.scale}
                paintOrder="stroke"
              >
                {t("lastKnown")}
              </text>
            </g>
          )}
          {calibrated &&
            showPlayers &&
            players
              .filter((p) => p.map_position)
              .map((p) => {
                const size = (p.player_id === selected ? 10 : 6) / camera.scale;
                const color = getThemeTeamColor(theme, p.team);
                return (
                  <g
                    key={p.player_id}
                    transform={`translate(${p.map_position.x * 1000} ${
                      p.map_position.y * 1000
                    })`}
                    role="button"
                    data-testid="player-map-marker"
                    data-player-id={p.player_id}
                    tabIndex={0}
                    aria-label={`${p.name} · ${p.team} · ${p.unit_name || "–"}`}
                    aria-pressed={selected === p.player_id}
                    style={{ cursor: isDragging ? "grabbing" : "pointer" }}
                    onClick={(e) => {
                      // Pointer clicks are handled on release because pointer
                      // capture retargets them to the SVG. Keep AT activation.
                      if (e.detail === 0) onSelect(p.player_id);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onSelect(p.player_id);
                      }
                    }}
                  >
                    {p.team === "axis" ? (
                      <path
                        d={`M 0 ${-size} L ${size} 0 L 0 ${size} L ${-size} 0 Z`}
                        fill={color}
                        stroke={theme.palette.background.default}
                        strokeWidth={2 / camera.scale}
                      />
                    ) : (
                      <circle
                        r={size}
                        fill={color}
                        stroke={theme.palette.background.default}
                        strokeWidth={2 / camera.scale}
                      />
                    )}
                    {selected === p.player_id && (
                      <text
                        data-testid="player-map-name"
                        x={12 / camera.scale}
                        y={4 / camera.scale}
                        fill={theme.palette.common.white}
                        stroke={theme.palette.common.black}
                        strokeWidth={3 / camera.scale}
                        paintOrder="stroke"
                        fontSize={14 / camera.scale}
                      >
                        {p.name}
                      </text>
                    )}
                  </g>
                );
              })}
        </g>
      </svg>
      {!calibrated && (
        <Box
          sx={{
            position: "absolute",
            top: "45%",
            left: "10%",
            right: "10%",
            p: 2,
            border: 1,
            borderColor: "warning.main",
            bgcolor: "background.paper",
            textAlign: "center",
            pointerEvents: "none",
          }}
        >
          <Typography fontWeight={800}>{t("uncalibrated")}</Typography>
          <Typography variant="body2">{t("uncalibratedHelp")}</Typography>
        </Box>
      )}
    </Box>
  );
}
