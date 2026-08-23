import {
  Box,
  Card,
  CardContent,
  Chip,
  Divider,
  Stack,
  Typography,
} from "@mui/material";

export default function ConfigFormSection({
  id,
  icon,
  eyebrow,
  title,
  description,
  status,
  statusColor = "default",
  action,
  children,
  footer,
  disabled = false,
  plain = false,
  testId,
  sx,
}) {
  const headingId = id ? `${id}-heading` : undefined;

  return (
    <Card
      component="section"
      id={id}
      data-testid={testId}
      aria-labelledby={headingId}
      variant="outlined"
      sx={{
        scrollMarginTop: 96,
        opacity: disabled ? 0.64 : 1,
        border: plain ? 0 : undefined,
        borderRadius: plain ? 0 : undefined,
        bgcolor: plain ? "transparent" : undefined,
        boxShadow: plain ? "none" : undefined,
        ...sx,
      }}
    >
      <Stack
        direction={{ xs: "column", sm: "row" }}
        justifyContent="space-between"
        alignItems={{ xs: "stretch", sm: "flex-start" }}
        spacing={1.5}
      >
        <Stack direction="row" spacing={1.25} sx={{ minWidth: 0 }}>
          {icon && !plain && (
            <Box
              sx={{
                display: "grid",
                placeItems: "center",
                flex: "0 0 auto",
                width: 40,
                height: 40,
                color: "primary.light",
                bgcolor: "action.selected",
                border: "1px solid",
                borderColor: "divider",
              }}
            >
              {icon}
            </Box>
          )}
          <Box sx={{ minWidth: 0 }}>
            {eyebrow && (
              <Typography
                variant="overline"
                color="primary.main"
                sx={{ display: "block", lineHeight: 1.25 }}
              >
                {eyebrow}
              </Typography>
            )}
            <Stack
              direction="row"
              alignItems="center"
              spacing={1}
              useFlexGap
              flexWrap="wrap"
            >
              <Typography
                id={headingId}
                component="h2"
                variant={plain ? "subtitle1" : "h6"}
                fontWeight={800}
                sx={
                  plain
                    ? { textTransform: "uppercase", letterSpacing: 0.4 }
                    : undefined
                }
              >
                {title}
              </Typography>
              {status && (
                <Chip label={status} color={statusColor} size="small" />
              )}
            </Stack>
            {description && (
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mt: 0.5, maxWidth: 760 }}
              >
                {description}
              </Typography>
            )}
          </Box>
        </Stack>
        {action && <Box sx={{ flexShrink: 0 }}>{action}</Box>}
      </Stack>

      {!plain && <Divider sx={{ my: 2 }} />}
      <CardContent
        aria-disabled={disabled}
        sx={plain ? { p: 0, pt: 2.5, "&:last-child": { pb: 0 } } : undefined}
      >
        {children}
      </CardContent>

      {footer && (
        <>
          {!plain && <Divider sx={{ my: 2 }} />}
          <Box>{footer}</Box>
        </>
      )}
    </Card>
  );
}
