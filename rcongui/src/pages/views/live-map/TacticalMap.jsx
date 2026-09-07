import { useEffect, useLayoutEffect, useRef, useState } from "react";
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
  events,
  showPlayers,
  encounter,
  t,
}) {
  const theme = useTheme();
  const [camera, setCamera] = useState({ x: 0, y: 0, scale: 1 });
  const [isDragging, setIsDragging] = useState(false);
  const drag = useRef(null);
  const svg = useRef(null);
  const nameLabel = useRef(null);
  const [nameWidth, setNameWidth] = useState(120);
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
  const selectedPlayer = players.find((p) => p.player_id === selected);
  const selectedCharacters = Array.from(selectedPlayer?.name || "");
  const selectedName =
    selectedCharacters.length > 32
      ? selectedCharacters.slice(0, 31).join("") + "…"
      : selectedCharacters.join("");
  const target = selectedPlayer?.map_position;
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
  useLayoutEffect(() => {
    let active = true;
    const measure = () => {
      if (active && nameLabel.current)
        setNameWidth(Math.ceil(nameLabel.current.getComputedTextLength()));
    };
    measure();
    document.fonts?.ready.then(measure);
    return () => {
      active = false;
    };
  }, [
    selected,
    selectedName,
    showPlayers,
    calibrated,
    theme.typography.fontFamily,
  ]);
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
        // Keyboard focus surrounds only the point, not point plus nameplate.
        "& [data-testid='player-map-marker']:focus-visible [data-marker-focus-ring]":
          {
            opacity: 1,
          },
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
            (events || []).map((event) => {
              const point = event.map_position;
              const color = event.teamkill
                ? theme.palette.error.main
                : theme.palette.warning.main;
              const size = 9 / camera.scale;
              return (
                <g
                  key={event.id}
                  data-testid="map-event-marker"
                  transform={`translate(${point.x * 1000} ${point.y * 1000})`}
                  pointerEvents="none"
                >
                  <title>
                    {t(event.teamkill ? "teamkill" : "kill")} ·{" "}
                    {event.attacker_name || event.attacker} →{" "}
                    {event.victim_name || event.victim}
                  </title>
                  {event.teamkill ? (
                    <path
                      d={`M ${-size} ${-size} L ${size} ${size} M ${size} ${-size} L ${-size} ${size}`}
                      fill="none"
                      stroke={color}
                      strokeWidth={3 / camera.scale}
                    />
                  ) : (
                    <circle
                      r={size}
                      fill="none"
                      stroke={color}
                      strokeWidth={3 / camera.scale}
                    />
                  )}
                </g>
              );
            })}
          {calibrated &&
            showPlayers &&
            players
              .filter((p) => p.map_position)
              .map((p) => {
                const size = (p.player_id === selected ? 7 : 6) / camera.scale;
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
                    style={{
                      cursor: isDragging ? "grabbing" : "pointer",
                      outline: "none",
                    }}
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
                    <rect
                      data-marker-focus-ring="true"
                      x={-14 / camera.scale}
                      y={-14 / camera.scale}
                      width={28 / camera.scale}
                      height={28 / camera.scale}
                      fill="none"
                      stroke={theme.palette.primary.main}
                      strokeWidth={2 / camera.scale}
                      strokeDasharray={`${3 / camera.scale} ${
                        2 / camera.scale
                      }`}
                      opacity={0}
                      pointerEvents="none"
                    />
                    {selected === p.player_id && (
                      <rect
                        data-testid="player-map-selection"
                        x={-10 / camera.scale}
                        y={-10 / camera.scale}
                        width={20 / camera.scale}
                        height={20 / camera.scale}
                        fill="none"
                        stroke={color}
                        strokeWidth={1 / camera.scale}
                        pointerEvents="none"
                      />
                    )}
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
                      <g transform={`scale(${1 / camera.scale})`}>
                        <rect
                          data-testid="player-map-nameplate"
                          x={16}
                          y={-12}
                          width={nameWidth + 14}
                          height={25}
                          fill={theme.palette.background.paper}
                          stroke={color}
                          strokeWidth={1}
                        />
                        <text
                          ref={nameLabel}
                          data-testid="player-map-name"
                          x={23}
                          y={5}
                          fill={theme.palette.text.primary}
                          fontFamily={theme.typography.fontFamily}
                          fontSize={14}
                        >
                          {selectedName}
                        </text>
                      </g>
                    )}
                  </g>
                );
              })}
        </g>
      </svg>
    </Box>
  );
}
