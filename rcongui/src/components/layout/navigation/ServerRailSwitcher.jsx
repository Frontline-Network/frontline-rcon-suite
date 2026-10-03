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
import KeyboardArrowDownRoundedIcon from "@mui/icons-material/KeyboardArrowDownRounded";
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

const POPOVER_ID = "global-server-switcher-popover";

export default function ServerRailSwitcher({
  variant = "rail",
  compact = false,
  label,
  value,
  tone,
}) {
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
  const isStatusTrigger = variant === "status";

  const trigger =
    variant === "select" ? (
      <ButtonBase
        id="wardogs-server-switcher-trigger"
        aria-label={triggerLabel}
        aria-haspopup="menu"
        aria-expanded={open ? "true" : undefined}
        aria-controls={open ? POPOVER_ID : undefined}
        onClick={(event) => setAnchorEl(event.currentTarget)}
        sx={{
          width: "100%",
          minHeight: 42,
          px: 1.5,
          gap: 2,
          justifyContent: "space-between",
          border: "1px solid",
          borderColor: "divider",
          borderRadius: "6px",
          color: "text.primary",
        }}
      >
        <Box
          aria-hidden
          sx={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            flexShrink: 0,
            bgcolor:
              state === CONNECTION_STATE.ONLINE
                ? "success.main"
                : state === CONNECTION_STATE.OFFLINE
                ? "error.main"
                : "warning.main",
          }}
        />
        <Typography variant="body2" noWrap sx={{ flex: 1, textAlign: "left" }}>
          {currentName}
        </Typography>
        <KeyboardArrowDownRoundedIcon sx={{ fontSize: 18 }} />
      </ButtonBase>
    ) : isStatusTrigger ? (
      <ButtonBase
        id="global-server-switcher-trigger"
        data-testid="global-server-switcher"
        aria-label={triggerLabel}
        aria-haspopup="menu"
        aria-expanded={open ? "true" : undefined}
        aria-controls={open ? POPOVER_ID : undefined}
        onClick={(event) => setAnchorEl(event.currentTarget)}
        sx={(theme) => ({
          position: "relative",
          gridArea: "server",
          width: "100%",
          minWidth: 0,
          minHeight: 44,
          height: "100%",
          justifyContent: "flex-start",
          gap: compact ? 0.55 : 0.75,
          px: compact ? 0.75 : 1.25,
          py: compact ? 0.5 : 0.8,
          borderRadius: "0 !important",
          color: "text.primary",
          textAlign: "left",
          bgcolor: open
            ? alpha(theme.palette.primary.main, 0.12)
            : "transparent",
          cursor: "pointer",
          transition: theme.transitions.create(
            ["background-color", "color", "box-shadow"],
            { duration: theme.transitions.duration.shortest }
          ),
          "&:hover": {
            color: "primary.light",
            bgcolor: alpha(theme.palette.primary.main, 0.08),
            boxShadow: `inset 0 -2px 0 ${theme.palette.primary.main}`,
          },
          "&:focus-visible": {
            outline: `2px solid ${theme.palette.primary.main}`,
            outlineOffset: -2,
          },
        })}
      >
        <Box
          aria-hidden
          sx={{
            position: "relative",
            display: "flex",
            flexShrink: 0,
            color: tone || "primary.main",
            "& svg": { fontSize: compact ? 16 : 18 },
          }}
        >
          <DnsOutlinedIcon />
          <Box
            sx={{
              position: "absolute",
              right: -2,
              bottom: -2,
              width: 6,
              height: 6,
              border: "1px solid",
              borderColor: "background.paper",
              bgcolor:
                state === CONNECTION_STATE.ONLINE
                  ? "success.main"
                  : state === CONNECTION_STATE.OFFLINE
                  ? "error.main"
                  : "warning.main",
            }}
          />
        </Box>
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Typography
            variant="caption"
            sx={{
              display: "block",
              color: "text.secondary",
              fontSize: compact ? "0.52rem" : "0.59rem",
              lineHeight: 1,
              letterSpacing: "0.055em",
              textTransform: "uppercase",
            }}
          >
            {label ||
              `${t("sidebar.serverNumber", {
                number: currentNumber ?? "–",
              })} · ${currentGameLabel}`}
          </Typography>
          <Typography
            variant="body2"
            sx={{
              mt: 0.25,
              fontSize: compact ? "0.7rem" : "0.8rem",
              fontWeight: 700,
              lineHeight: 1.15,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {value || currentName}
          </Typography>
        </Box>
        <Stack
          aria-hidden
          direction="row"
          alignItems="center"
          spacing={0.25}
          sx={{
            alignSelf: "stretch",
            flexShrink: 0,
            pl: compact ? 0.25 : 0.75,
            borderLeft: "1px solid",
            borderColor: "divider",
            color: open ? "primary.light" : "text.secondary",
          }}
        >
          {!compact && (
            <Typography
              component="span"
              sx={{
                fontSize: "0.5rem",
                fontWeight: 700,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
              }}
            >
              {t("sidebar.switchServer")}
            </Typography>
          )}
          <KeyboardArrowDownRoundedIcon
            sx={(theme) => ({
              fontSize: compact ? 18 : 20,
              transform: open ? "rotate(180deg)" : "rotate(0deg)",
              transition: theme.transitions.create("transform", {
                duration: theme.transitions.duration.shortest,
              }),
            })}
          />
        </Stack>
      </ButtonBase>
    ) : (
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
    );

  return (
    <>
      <Tooltip
        title={isStatusTrigger ? t("sidebar.switchServer") : triggerLabel}
        placement={isStatusTrigger ? "bottom" : "right"}
        arrow
        enterDelay={350}
        slotProps={{ tooltip: { sx: { borderRadius: 0 } } }}
      >
        {trigger}
      </Tooltip>

      <Popover
        id={POPOVER_ID}
        open={open}
        anchorEl={anchorEl}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={
          isStatusTrigger
            ? { vertical: "bottom", horizontal: "left" }
            : { vertical: "top", horizontal: "right" }
        }
        transformOrigin={
          isStatusTrigger
            ? { vertical: "top", horizontal: "left" }
            : { vertical: "top", horizontal: "left" }
        }
        slotProps={{
          paper: {
            sx: {
              width: { xs: "calc(100vw - 72px)", sm: 310 },
              maxWidth: 310,
              mt: isStatusTrigger ? 0.75 : 0,
              ml: isStatusTrigger ? 0 : { xs: 0, sm: 1 },
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
            id="global-server-switcher-title"
            variant="caption"
            sx={{ color: "primary.light", textTransform: "uppercase" }}
          >
            {t("sidebar.switchServer")}
          </Typography>
        </Stack>
        <MenuList
          autoFocusItem
          aria-labelledby="global-server-switcher-title"
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
