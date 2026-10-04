import { Box, Stack, Typography } from "@mui/material";
import { useLocation } from "react-router-dom";
import NavbarBreadcrumbs from "../NavbarBreadcrumbs";
import ServerRailSwitcher from "../navigation/ServerRailSwitcher";

export default function WardogsPageFrame({ children, active = true }) {
  const { pathname } = useLocation();
  const family = pathname.startsWith("/settings/maps")
    ? "maps"
    : pathname.startsWith("/settings")
    ? "settings"
    : pathname.startsWith("/records")
    ? "records"
    : pathname.startsWith("/stats")
    ? "stats"
    : pathname.startsWith("/views")
    ? "live"
    : pathname === "/"
    ? "dashboard"
    : "other";
  return (
    <Box
      className={active ? "wardogs-page" : undefined}
      data-page-family={active ? family : undefined}
      sx={{
        display: active ? "block" : "contents",
        width: "100%",
        minWidth: 0,
        flex: 1,
        position: "relative",
      }}
    >
      {active && (
        <Stack
          className="wardogs-page-context"
          direction={{ xs: "column", sm: "row" }}
          alignItems={{ sm: "center" }}
          justifyContent="space-between"
          gap={1.5}
          sx={{ mb: 2, minHeight: { sm: 42 } }}
        >
          <Box sx={{ minWidth: 0 }}>
            <NavbarBreadcrumbs />
          </Box>
          {!pathname.startsWith("/administration") && !pathname.startsWith("/documentation") && !pathname.startsWith("/updates") && !pathname.startsWith("/account/") && <Box
            sx={{
              width: { xs: "100%", sm: 248 },
              flexShrink: 0,
            }}
          >
            <ServerRailSwitcher variant="select" />
          </Box>}
        </Stack>
      )}
      <Box
        className={active ? "wardogs-page-content" : undefined}
        sx={{ minWidth: 0, display: active ? "block" : "contents" }}
      >
        {children}
      </Box>
      {active && (
        <Stack
          component="footer"
          direction="row"
          justifyContent="space-between"
          sx={{ py: 4, mt: 1, color: "text.disabled" }}
        >
          <Typography variant="caption">FRONTLINE / CRCON</Typography>
          <Typography variant="caption">Aurora</Typography>
        </Stack>
      )}
    </Box>
  );
}
