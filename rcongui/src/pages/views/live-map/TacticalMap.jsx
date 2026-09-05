import { useEffect, useRef, useState } from "react";
import { Box, Button, Stack, Typography, useTheme } from "@mui/material";
import { getThemeTeamColor } from "@/themes/teamColors";
import { getTacticalMapImageSrc } from "@/utils/map-images.mjs";

export default function TacticalMap({
  frame,
  players,
  selected,
  following,
  onSelect,
  trails,
  showNames,
  showPlayers,
  encounter,
  t,
}) {
  const theme = useTheme();
  const [camera, setCamera] = useState({ x: 0, y: 0, scale: 1 });
  const drag = useRef(null);
  const svg = useRef(null);
  const mapId = frame?.map?.id;
  useEffect(() => {
    setCamera({ x: 0, y: 0, scale: 1 });
  }, [mapId]);
  const target = players.find((p) => p.player_id === selected)?.map_position;
  useEffect(() => {
    if (following && target)
      setCamera((c) => ({
        ...c,
        x: 0.5 - target.x * c.scale,
        y: 0.5 - target.y * c.scale,
      }));
  }, [following, target?.x, target?.y]);
  const calibrated = Boolean(frame?.calibration?.verified);
  const encounterPoint =
    calibrated && encounter?.round_id === frame?.round_id
      ? encounter.map_position
      : null;
  const image = getTacticalMapImageSrc(frame?.map);
  const zoom = (factor) =>
    setCamera((c) => {
      const scale = Math.max(1, Math.min(8, c.scale * factor));
      return {
        scale,
        x: 0.5 - ((0.5 - c.x) * scale) / c.scale,
        y: 0.5 - ((0.5 - c.y) * scale) / c.scale,
      };
    });
  const onMove = (e) => {
    if (!drag.current) return;
    const rect = svg.current.getBoundingClientRect();
    const size = Math.min(rect.width, rect.height);
    const dx = (e.clientX - drag.current.x) / size;
    const dy = (e.clientY - drag.current.y) / size;
    setCamera((c) => ({ ...c, x: c.x + dx, y: c.y + dy }));
    drag.current = { x: e.clientX, y: e.clientY };
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
          onClick={() => setCamera({ x: 0, y: 0, scale: 1 })}
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
          cursor: drag.current ? "grabbing" : "grab",
        }}
        onPointerDown={(e) => {
          if (e.target === e.currentTarget || e.target.tagName === "image") {
            drag.current = { x: e.clientX, y: e.clientY };
            e.currentTarget.setPointerCapture(e.pointerId);
          }
        }}
        onPointerMove={onMove}
        onPointerUp={() => {
          drag.current = null;
        }}
        onPointerCancel={() => {
          drag.current = null;
        }}
      >
        <g
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
                    tabIndex={0}
                    aria-label={`${p.name} · ${p.team} · ${p.unit_name || "–"}`}
                    aria-pressed={selected === p.player_id}
                    style={{ cursor: "pointer" }}
                    onClick={() => onSelect(p.player_id)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onSelect(p.player_id);
                      }
                    }}
                  >
                    <title>{`${p.name} · ${p.role} · ${
                      p.unit_name || "–"
                    }`}</title>
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
                    {((showNames && camera.scale >= 2) ||
                      selected === p.player_id) && (
                      <text
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
