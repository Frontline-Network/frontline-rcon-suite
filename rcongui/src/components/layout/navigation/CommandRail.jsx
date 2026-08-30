import { createElement, isValidElement } from "react";
import {
  Badge,
  Box,
  Divider,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import { alpha } from "@mui/material/styles";

export const COMMAND_RAIL_WIDTH = 64;

const renderIcon = (icon) => {
  if (!icon) return null;
  return isValidElement(icon) ? icon : createElement(icon);
};

function RailAction({ item, active, current, onActivate }) {
  const button = (
    <IconButton
      aria-label={item.ariaLabel || item.label}
      aria-current={current ? "page" : undefined}
      aria-controls={item.ariaControls}
      aria-expanded={item.ariaControls ? Boolean(item.expanded) : undefined}
      data-workspace-id={item.workspaceId || undefined}
      disabled={item.disabled}
      onClick={(event) => onActivate?.(item.id, event)}
      sx={(theme) => ({
        position: "relative",
        width: 48,
        height: 44,
        minWidth: 44,
        borderRadius: 0,
        border: "1px solid transparent",
        color: active ? "primary.light" : "text.secondary",
        bgcolor: active ? "action.selected" : "transparent",
        transition: theme.transitions.create(
          ["color", "background-color", "border-color"],
          { duration: theme.transitions.duration.shortest }
        ),
        "&::before": {
          content: '""',
          position: "absolute",
          top: 7,
          bottom: 7,
          left: -1,
          width: 3,
          bgcolor: active ? "primary.main" : "transparent",
        },
        "&:hover": {
          color: "primary.light",
          bgcolor: alpha(theme.palette.primary.main, 0.1),
          borderColor: alpha(theme.palette.primary.light, 0.18),
        },
        "&:focus-visible": {
          outline: `2px solid ${theme.palette.primary.main}`,
          outlineOffset: -2,
        },
        "&.Mui-disabled": {
          color: "text.disabled",
        },
        "& svg": {
          width: 20,
          height: 20,
        },
      })}
    >
      {item.badge ? (
        <Badge
          color={item.badgeColor || "error"}
          badgeContent={item.badge}
          max={99}
          sx={{
            "& .MuiBadge-badge": {
              minWidth: 15,
              height: 15,
              px: 0.4,
              borderRadius: 0,
              fontSize: 9,
              fontWeight: 900,
            },
          }}
        >
          {renderIcon(item.icon)}
        </Badge>
      ) : (
        renderIcon(item.icon)
      )}
    </IconButton>
  );

  return (
    <Tooltip title={item.label} placement="right" arrow enterDelay={450}>
      <span>{button}</span>
    </Tooltip>
  );
}

/**
 * Persistent, route-agnostic workspace rail. Callers provide MUI icon
 * components or elements and connect the item ids to their own navigation.
 */
export default function CommandRail({
  workspaces = [],
  utilityItems = [],
  statusItems = [],
  activeWorkspaceId,
  currentWorkspaceId = activeWorkspaceId,
  onWorkspaceChange,
  onUtilityActivate,
  brandLabel = "Frontline Network",
  logoSrc = "/frontline-logo.png",
  ariaLabel = "Arbeitsbereiche",
  topSlot,
  bottomSlot,
}) {
  return (
    <Box
      component="aside"
      data-testid="desktop-command-rail"
      sx={{
        width: COMMAND_RAIL_WIDTH,
        minWidth: COMMAND_RAIL_WIDTH,
        height: "100dvh",
        bgcolor: "grey.900",
        borderRight: "1px solid",
        borderColor: "divider",
      }}
    >
      <Stack sx={{ height: "100%", alignItems: "center" }}>
        <Tooltip title={brandLabel} placement="right" arrow>
          <Box
            sx={{
              width: "100%",
              height: 64,
              display: "grid",
              placeItems: "center",
              flexShrink: 0,
            }}
          >
            <Box
              component="img"
              src={logoSrc}
              alt={brandLabel}
              sx={{ width: 40, height: 34, objectFit: "contain" }}
            />
          </Box>
        </Tooltip>

        {topSlot}
        <Divider flexItem />

        <Stack
          component="nav"
          aria-label={ariaLabel}
          spacing={0.5}
          sx={{
            width: "100%",
            alignItems: "center",
            py: 1,
            overflowY: "auto",
            scrollbarWidth: "none",
            "&::-webkit-scrollbar": { display: "none" },
          }}
        >
          {workspaces.map((item) => (
            <RailAction
              key={item.id}
              item={item}
              active={item.id === activeWorkspaceId}
              current={item.id === currentWorkspaceId}
              onActivate={onWorkspaceChange}
            />
          ))}
        </Stack>

        <Stack
          spacing={0.75}
          sx={{ mt: "auto", pb: 0.75, alignItems: "center" }}
        >
          {statusItems.length > 0 && (
            <Stack
              direction="row"
              aria-label="Systemstatus"
              spacing={0.5}
              sx={{ px: 0.75, pb: 0.25 }}
            >
              {statusItems.map((status) => (
                <Tooltip
                  key={status.id}
                  title={status.label}
                  placement="right"
                  arrow
                >
                  <Box
                    component="span"
                    aria-label={status.label}
                    sx={{
                      width: 7,
                      height: 7,
                      bgcolor: status.color || "text.disabled",
                      border: "1px solid",
                      borderColor: "background.default",
                    }}
                  />
                </Tooltip>
              ))}
            </Stack>
          )}

          {utilityItems.map((item) => (
            <RailAction
              key={item.id}
              item={item}
              active={item.id === activeWorkspaceId}
              current={false}
              onActivate={onUtilityActivate}
            />
          ))}
          {bottomSlot}
          <Typography
            aria-hidden
            sx={{
              color: "text.disabled",
              fontSize: 8,
              fontWeight: 900,
              letterSpacing: "0.16em",
              lineHeight: 1,
            }}
          >
            FLN
          </Typography>
        </Stack>
      </Stack>
    </Box>
  );
}
