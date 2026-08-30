import { useMemo, useState } from "react";
import {
  Box,
  ButtonBase,
  MenuItem,
  MenuList,
  Popover,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import DnsOutlinedIcon from "@mui/icons-material/DnsOutlined";
import { alpha } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import { useGlobalStore } from "@/stores/global-state";
import { getGameLabel, normalizeGame } from "@/utils/game-context";
import { CONNECTION_STATE } from "@/utils/connectionHealth";
import {
  buildServerOptions,
  getServerHref,
  getServerShortCode,
} from "./server-switching.mjs";

const POPOVER_ID = "server-rail-switcher-popover";

export default function ServerRailSwitcher() {
  const { t } = useTranslation();
  const currentServer = useGlobalStore((state) => state.serverState);
  const peerServers = useGlobalStore((state) => state.servers);
  const connectionState = useGlobalStore(
    (state) => state.connectionHealth?.crcon?.state
  );
  const [anchorEl, setAnchorEl] = useState(null);
  const servers = useMemo(
    () => buildServerOptions(currentServer, peerServers),
    [currentServer, peerServers]
  );
  const open = Boolean(anchorEl);
  const currentName =
    currentServer?.short_name || currentServer?.name || t("common.unknown");
  const currentNumber = currentServer?.server_number;
  const currentGameLabel = getGameLabel(normalizeGame(currentServer?.game));
  const state = connectionState ?? CONNECTION_STATE.UNKNOWN;
  const stateLabel = t(`connectionStates.${state}`);
  const triggerLabel = [
    `${t("sidebar.selectServer")}: ${currentName}`,
    t("sidebar.serverNumber", { number: currentNumber ?? "–" }),
    currentGameLabel,
    stateLabel,
  ]
    .filter(Boolean)
    .join(", ");

  return (
    <>
      <Tooltip
        title={triggerLabel}
        placement="right"
        arrow
        enterDelay={450}
        slotProps={{ tooltip: { sx: { borderRadius: 0 } } }}
      >
        <ButtonBase
          id="server-rail-switcher-trigger"
          data-testid="server-rail-switcher"
          aria-label={triggerLabel}
          aria-haspopup="menu"
          aria-expanded={open ? "true" : undefined}
          aria-controls={open ? POPOVER_ID : undefined}
          onClick={(event) => setAnchorEl(event.currentTarget)}
          sx={(theme) => ({
            position: "relative",
            width: 48,
            height: 44,
            my: 0.75,
            borderRadius: "0 !important",
            border: "1px solid",
            borderColor: open
              ? "primary.main"
              : alpha(theme.palette.primary.light, 0.22),
            color: open ? "primary.light" : "text.primary",
            bgcolor: open
              ? alpha(theme.palette.primary.main, 0.14)
              : alpha(theme.palette.background.default, 0.34),
            transition: theme.transitions.create(
              ["color", "background-color", "border-color"],
              { duration: theme.transitions.duration.shortest }
            ),
            "&:hover": {
              color: "primary.light",
              borderColor: "primary.main",
              bgcolor: alpha(theme.palette.primary.main, 0.12),
            },
            "&:focus-visible": {
              outline: `2px solid ${theme.palette.primary.main}`,
              outlineOffset: -2,
            },
          })}
        >
          <Typography
            component="span"
            sx={{
              fontFamily:
                '"Bahnschrift Condensed", "Arial Narrow", Bahnschrift, sans-serif',
              fontSize: 17,
              fontWeight: 700,
              letterSpacing: "0.04em",
            }}
          >
            {getServerShortCode(currentServer)}
          </Typography>
          <Box
            aria-hidden
            sx={{
              position: "absolute",
              right: 5,
              bottom: 5,
              width: 7,
              height: 7,
              border: "1px solid",
              borderColor: "background.default",
              bgcolor:
                state === CONNECTION_STATE.ONLINE
                  ? "success.main"
                  : state === CONNECTION_STATE.OFFLINE
                  ? "error.main"
                  : "warning.main",
            }}
          />
        </ButtonBase>
      </Tooltip>

      <Popover
        id={POPOVER_ID}
        open={open}
        anchorEl={anchorEl}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{ vertical: "top", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "left" }}
        slotProps={{
          paper: {
            sx: {
              width: { xs: "calc(100vw - 72px)", sm: 310 },
              maxWidth: 310,
              ml: { xs: 0, sm: 1 },
              borderRadius: "0 !important",
              border: "1px solid",
              borderColor: "divider",
              backgroundImage: "none",
              bgcolor: "background.paper",
              boxShadow: 12,
            },
          },
        }}
      >
        <Stack
          direction="row"
          alignItems="center"
          spacing={1}
          sx={{
            px: 1.5,
            minHeight: 42,
            borderBottom: "1px solid",
            borderColor: "divider",
          }}
        >
          <DnsOutlinedIcon
            aria-hidden
            sx={{ color: "primary.main", fontSize: 18 }}
          />
          <Typography
            id="server-rail-switcher-title"
            variant="caption"
            sx={{ color: "primary.light", textTransform: "uppercase" }}
          >
            {t("sidebar.switchServer")}
          </Typography>
        </Stack>
        <MenuList
          autoFocusItem
          aria-labelledby="server-rail-switcher-title"
          sx={{ p: 0 }}
        >
          {servers.map((server) => {
            const isCurrent = server.server_number === currentNumber;
            const gameLabel = getGameLabel(normalizeGame(server.game));
            const name = server.short_name || server.name || "<server_name>";

            return (
              <MenuItem
                key={server.server_number ?? server.link ?? server.port}
                component="a"
                href={getServerHref(server, window.location.href)}
                aria-current={isCurrent ? "true" : undefined}
                onClick={(event) => {
                  if (isCurrent) {
                    event.preventDefault();
                    setAnchorEl(null);
                  }
                }}
                sx={(theme) => ({
                  minHeight: 50,
                  px: 1.25,
                  gap: 1,
                  borderRadius: "0 !important",
                  borderBottom: "1px solid",
                  borderColor: "divider",
                  color: isCurrent ? "text.primary" : "text.secondary",
                  bgcolor: isCurrent
                    ? alpha(theme.palette.primary.main, 0.1)
                    : "transparent",
                  borderLeft: "2px solid",
                  borderLeftColor: isCurrent ? "primary.main" : "transparent",
                  "&:hover": {
                    color: "text.primary",
                    bgcolor: alpha(theme.palette.primary.main, 0.08),
                  },
                })}
              >
                <Box
                  aria-hidden
                  sx={{
                    width: 28,
                    height: 28,
                    display: "grid",
                    placeItems: "center",
                    flexShrink: 0,
                    border: "1px solid",
                    borderColor: "divider",
                    fontSize: 12,
                    fontWeight: 700,
                  }}
                >
                  {server.server_number ?? "–"}
                </Box>
                <Box sx={{ minWidth: 0, flex: 1 }}>
                  <Typography
                    noWrap
                    sx={{ fontSize: 12.5, fontWeight: isCurrent ? 700 : 500 }}
                  >
                    {name}
                  </Typography>
                  <Typography variant="caption" sx={{ color: "text.disabled" }}>
                    {t("sidebar.serverNumber", {
                      number: server.server_number ?? "–",
                    })}
                  </Typography>
                </Box>
                {isCurrent && (
                  <Typography
                    component="span"
                    variant="caption"
                    sx={{
                      px: 0.6,
                      py: 0.2,
                      border: "1px solid",
                      borderColor: "primary.dark",
                      color: "primary.light",
                      lineHeight: 1,
                    }}
                  >
                    {t("sidebar.currentServer")}
                  </Typography>
                )}
                {gameLabel && (
                  <Typography
                    component="span"
                    variant="caption"
                    sx={{
                      minWidth: 34,
                      px: 0.5,
                      py: 0.2,
                      border: "1px solid",
                      borderColor: "divider",
                      color: "text.secondary",
                      textAlign: "center",
                      lineHeight: 1,
                    }}
                  >
                    {gameLabel === "HLL: Vietnam" ? "HLLV" : gameLabel}
                  </Typography>
                )}
              </MenuItem>
            );
          })}
        </MenuList>
      </Popover>
    </>
  );
}
