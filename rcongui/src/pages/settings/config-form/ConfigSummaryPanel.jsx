import {
  Alert,
  Box,
  Card,
  CardContent,
  Divider,
  Stack,
  Typography,
} from "@mui/material";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";

const toneColor = {
  success: "success.main",
  warning: "warning.main",
  error: "error.main",
  info: "info.main",
  default: "text.primary",
};

export default function ConfigSummaryPanel({
  title,
  description,
  items = [],
  notice,
  noticeSeverity = "info",
  emptyLabel,
  children,
}) {
  return (
    <Card component="aside" variant="outlined" aria-label={title}>
      <Stack direction="row" spacing={1} alignItems="flex-start">
        <CheckCircleOutlineIcon color="primary" sx={{ mt: 0.25 }} />
        <Box>
          <Typography component="h2" variant="subtitle1" fontWeight={800}>
            {title}
          </Typography>
          {description && (
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ mt: 0.25 }}
            >
              {description}
            </Typography>
          )}
        </Box>
      </Stack>

      <Divider sx={{ my: 2 }} />
      <CardContent>
        <Stack spacing={1.5}>
          {items.map((item) => (
            <Box data-theme-surface="panel"
              key={item.id || item.label}
              sx={{
                p: 1.25,
                border: "1px solid",
                borderColor: "divider",
                bgcolor: "background.default",
              }}
            >
              <Stack direction="row" spacing={1} alignItems="flex-start">
                {item.icon && (
                  <Box
                    sx={{
                      display: "inline-flex",
                      mt: 0.25,
                      color: toneColor[item.tone] || toneColor.default,
                    }}
                  >
                    {item.icon}
                  </Box>
                )}
                <Box sx={{ minWidth: 0 }}>
                  <Typography variant="caption" color="text.secondary">
                    {item.label}
                  </Typography>
                  <Typography
                    component="div"
                    variant="body2"
                    fontWeight={750}
                    color={toneColor[item.tone] || toneColor.default}
                    sx={{ overflowWrap: "anywhere" }}
                  >
                    {item.value}
                  </Typography>
                  {item.description && (
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ display: "block", mt: 0.25 }}
                    >
                      {item.description}
                    </Typography>
                  )}
                </Box>
              </Stack>
            </Box>
          ))}

          {!items.length && emptyLabel && (
            <Typography variant="body2" color="text.secondary">
              {emptyLabel}
            </Typography>
          )}

          {children}
          {notice && <Alert severity={noticeSeverity}>{notice}</Alert>}
        </Stack>
      </CardContent>
    </Card>
  );
}
