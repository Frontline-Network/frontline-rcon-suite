import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

const emptyPoints = () =>
  Array.from({ length: 5 }, () => ({ x: "", y: "", u: "", v: "" }));

export default function CalibrationPanel({ frame, mutation, t }) {
  const [points, setPoints] = useState(emptyPoints);
  const [source, setSource] = useState("");
  const [scale, setScale] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const ready =
    frame?.map?.map?.id &&
    source.trim() &&
    Number(scale) > 0 &&
    points.every(
      (p) =>
        Object.values(p).every((v) => v !== "" && Number.isFinite(Number(v))) &&
        [p.u, p.v].every((v) => Number(v) >= 0 && Number(v) <= 100)
    );
  const change = (i, key, value) => {
    setConfirmed(false);
    setPoints((old) =>
      old.map((p, n) => (n === i ? { ...p, [key]: value } : p))
    );
  };
  const submit = () => {
    const mapped = points.map((p) => ({
      x: Number(p.x),
      y: Number(p.y),
      u: Number(p.u) / 100,
      v: Number(p.v) / 100,
    }));
    mutation.mutate({
      path: "calibration",
      data: {
        map_id: frame.map.map.id,
        source,
        units_per_meter: Number(scale),
        anchors: mapped.slice(0, 3),
        checks: mapped.slice(3),
      },
    });
    setConfirmed(false);
  };
  return (
    <Box
      component="details"
      sx={{
        border: 1,
        borderColor: "divider",
        bgcolor: "background.paper",
        mt: 1,
        p: 1.5,
      }}
    >
      <Typography
        component="summary"
        fontWeight={800}
        sx={{ cursor: "pointer" }}
      >
        {t("calibrationTitle")}
      </Typography>
      <Alert severity="warning" sx={{ my: 1 }}>
        {t("calibrationHelp")}
      </Alert>
      <Stack gap={1}>
        <TextField
          size="small"
          label={t("calibrationSource")}
          value={source}
          onChange={(e) => {
            setConfirmed(false);
            setSource(e.target.value);
          }}
        />
        <TextField
          size="small"
          type="number"
          label={t("unitsPerMeter")}
          value={scale}
          onChange={(e) => {
            setConfirmed(false);
            setScale(e.target.value);
          }}
        />
        {points.map((point, i) => (
          <Box key={i} sx={{ borderTop: 1, borderColor: "divider", pt: 1 }}>
            <Typography variant="caption">
              {t(i < 3 ? "anchor" : "checkPoint")} {i < 3 ? i + 1 : i - 2}
            </Typography>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr 1fr", md: "repeat(4, 1fr)" },
                gap: 1,
                mt: 1,
              }}
            >
              {["x", "y", "u", "v"].map((key) => (
                <TextField
                  key={key}
                  size="small"
                  type="number"
                  label={
                    key === "u"
                      ? t("imageX")
                      : key === "v"
                      ? t("imageY")
                      : `World ${key.toUpperCase()}`
                  }
                  value={point[key]}
                  onChange={(e) => change(i, key, e.target.value)}
                />
              ))}
            </Box>
          </Box>
        ))}
        <Typography variant="caption">{t("calibrationCoordinates")}</Typography>
        {confirmed ? (
          <Stack gap={1}>
            <Alert severity="warning">
              {t("calibrationConfirm")} · {frame.map.pretty_name}
            </Alert>
            <Button
              variant="contained"
              disabled={!ready || mutation.isPending}
              onClick={submit}
            >
              {t("calibrationSave")}
            </Button>
          </Stack>
        ) : (
          <Button
            disabled={!ready || mutation.isPending}
            onClick={() => setConfirmed(true)}
          >
            {t("calibrationCheck")}
          </Button>
        )}
      </Stack>
    </Box>
  );
}
