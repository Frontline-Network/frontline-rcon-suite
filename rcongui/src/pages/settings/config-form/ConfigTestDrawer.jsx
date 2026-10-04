import {
  Alert,
  Box,
  Button,
  Divider,
  Drawer,
  IconButton,
  Stack,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import ScienceOutlinedIcon from "@mui/icons-material/ScienceOutlined";
import { useEffect, useRef } from "react";

const toneSeverity = {
  success: "success",
  warning: "warning",
  error: "error",
  info: "info",
};

export default function ConfigTestDrawer({
  open,
  onClose,
  title,
  description,
  notice,
  children,
  result,
  resultLabel,
  runLabel,
  closeLabel,
  onRun,
}) {
  const resultRef = useRef(null);

  useEffect(() => {
    if (result) resultRef.current?.scrollIntoView({ block: "nearest" });
  }, [result]);

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{
        component: "section",
        role: "dialog",
        "aria-modal": "true",
        "aria-labelledby": "config-test-drawer-title",
        sx: {
          width: { xs: "100%", sm: 480 },
          maxWidth: "100vw",
          borderRadius: 0,
          borderLeft: "1px solid",
          borderColor: "divider",
          bgcolor: "background.paper",
        },
      }}
    >
      <Stack sx={{ minHeight: "100%" }}>
        <Stack
          direction="row"
          spacing={1.5}
          alignItems="flex-start"
          sx={{ p: { xs: 2, sm: 2.5 } }}
        >
          <Box data-theme-surface="control"
            sx={{
              display: "grid",
              placeItems: "center",
              width: 40,
              height: 40,
              flex: "0 0 auto",
              border: "1px solid",
              borderColor: "primary.main",
              color: "primary.main",
              bgcolor: "action.selected",
            }}
          >
            <ScienceOutlinedIcon />
          </Box>
          <Box sx={{ minWidth: 0, flex: 1 }}>
            <Typography
              id="config-test-drawer-title"
              component="h2"
              variant="h6"
              fontWeight={850}
            >
              {title}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {description}
            </Typography>
          </Box>
          <IconButton
            onClick={onClose}
            aria-label={closeLabel}
            sx={{ borderRadius: 0 }}
          >
            <CloseIcon />
          </IconButton>
        </Stack>

        <Divider />
        <Stack spacing={2} sx={{ p: { xs: 2, sm: 2.5 }, flex: 1 }}>
          {notice && <Alert severity="info">{notice}</Alert>}
          {children}
          <Button
            variant="contained"
            startIcon={<ScienceOutlinedIcon />}
            onClick={onRun}
            sx={{ minHeight: 44 }}
          >
            {runLabel}
          </Button>

          {result && (
            <Box data-theme-surface="panel"
              ref={resultRef}
              aria-live="polite"
              sx={{
                border: "1px solid",
                borderColor: `${result.tone || "info"}.main`,
                bgcolor: "background.default",
                p: 2,
              }}
            >
              <Typography variant="overline" color="text.secondary">
                {resultLabel}
              </Typography>
              <Alert
                severity={toneSeverity[result.tone] || "info"}
                icon={false}
                sx={{ mt: 0.75 }}
              >
                <Typography variant="subtitle2" fontWeight={850}>
                  {result.title}
                </Typography>
                <Typography variant="body2" sx={{ mt: 0.5 }}>
                  {result.description}
                </Typography>
              </Alert>
              {result.steps?.length > 0 && (
                <Stack
                  direction="row"
                  spacing={0.75}
                  useFlexGap
                  flexWrap="wrap"
                  sx={{ mt: 1.5 }}
                >
                  {result.steps.map((step, index) => (
                    <Box data-theme-surface="panel"
                      key={`${step}-${index}`}
                      sx={{
                        px: 1,
                        py: 0.75,
                        border: "1px solid",
                        borderColor: "divider",
                        fontSize: 12,
                        fontWeight: 800,
                      }}
                    >
                      {index + 1}. {step}
                    </Box>
                  ))}
                </Stack>
              )}
            </Box>
          )}
        </Stack>
      </Stack>
    </Drawer>
  );
}
