import { createElement, isValidElement } from "react";
import {
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import { alpha } from "@mui/material/styles";
import { NavLink } from "react-router-dom";
import { getContextNavigationSurface } from "./navigation-surfaces";

export const CONTEXT_NAVIGATION_PANEL_WIDTH = 244;

const renderIcon = (icon) => {
  if (!icon) return null;
  return isValidElement(icon) ? icon : createElement(icon);
};

function ContextNavigationItem({ item, active, onSelect }) {
  const locked = Boolean(item.locked || item.disabled);
  const linkProps =
    !locked && item.href
      ? {
          component: NavLink,
          to: item.href,
          end: item.href === "/" || item.href === "/apps",
        }
      : {};

  const button = (
    <ListItemButton
      {...linkProps}
      aria-current={active ? "page" : undefined}
      aria-disabled={locked || undefined}
      onClick={(event) => {
        if (locked) {
          event.preventDefault();
          return;
        }
        onSelect?.(item.id, item);
      }}
      sx={(theme) => ({
        position: "relative",
        minHeight: 46,
        px: 1.25,
        py: 0.5,
        borderRadius: "0 !important",
        borderLeft: "2px solid",
        borderLeftColor: active ? "primary.main" : "transparent",
        borderBottom: "1px solid",
        borderBottomColor: "divider",
        color: active ? "primary.light" : "text.secondary",
        bgcolor: active
          ? alpha(theme.palette.primary.main, 0.11)
          : "transparent",
        cursor: locked ? "not-allowed" : "pointer",
        "&:hover": {
          color: active ? "primary.light" : "text.primary",
          bgcolor: active
            ? alpha(theme.palette.primary.main, 0.15)
            : "action.hover",
        },
        "&:focus-visible": {
          outline: `2px solid ${theme.palette.primary.main}`,
          outlineOffset: -2,
        },
        ...(locked && { color: "text.disabled" }),
      })}
    >
      {item.icon && (
        <ListItemIcon
          sx={{
            minWidth: 38,
            color: "inherit",
            "& svg": { width: 18, height: 18 },
          }}
        >
          {renderIcon(item.icon)}
        </ListItemIcon>
      )}
      <ListItemText
        primary={item.label}
        secondary={item.description}
        primaryTypographyProps={{
          fontSize: 13,
          fontWeight: active ? 700 : 400,
          lineHeight: 1.25,
        }}
        secondaryTypographyProps={{
          fontSize: 10,
          lineHeight: 1.3,
          color: "text.disabled",
          noWrap: true,
        }}
      />
      {item.badge != null && (
        <Typography
          component="span"
          variant="caption"
          sx={{
            ml: 1,
            minWidth: 20,
            px: 0.5,
            py: 0.15,
            border: "1px solid",
            borderColor: active ? "primary.dark" : "divider",
            color: active ? "primary.light" : "text.disabled",
            textAlign: "center",
            lineHeight: 1.2,
          }}
        >
          {item.badge}
        </Typography>
      )}
      {locked && <LockOutlinedIcon aria-hidden sx={{ ml: 1, fontSize: 16 }} />}
    </ListItemButton>
  );

  return (
    <ListItem disablePadding>
      {locked ? (
        <Tooltip
          title={item.lockedReason || ""}
          placement="right"
          arrow
          slotProps={{ tooltip: { sx: { borderRadius: 0 } } }}
        >
          {button}
        </Tooltip>
      ) : (
        button
      )}
    </ListItem>
  );
}

export default function ContextNavigationPanel({
  workspaceLabel,
  workspaceCode,
  workspaceDescription,
  sections = [],
  activeItemId,
  onItemSelect,
  ariaLabel,
  width = CONTEXT_NAVIGATION_PANEL_WIDTH,
  emptyMessage = "No matching pages found.",
  statusItems = [],
  id = "desktop-navigation-panel",
  presentation = "persistent",
  onKeyDown,
}) {
  const visibleSections = sections.filter(
    (section) => section.items.length > 0
  );

  return (
    <Box
      component="aside"
      id={id}
      data-testid="desktop-navigation-panel"
      data-presentation={presentation}
      onKeyDown={onKeyDown}
      sx={(theme) => ({
        width,
        minWidth: width,
        height: "100dvh",
        ...getContextNavigationSurface(theme),
        borderRight: "1px solid",
        borderColor: "divider",
      })}
    >
      <Stack sx={{ height: "100%", minHeight: 0 }}>
        <Box
          sx={{
            px: 1.75,
            pt: 1.75,
            pb: 1.35,
            borderBottom: "1px solid",
            borderColor: "divider",
          }}
        >
          {workspaceCode && (
            <Typography
              variant="caption"
              sx={{
                display: "block",
                mb: 0.4,
                color: "primary.main",
                letterSpacing: "0.16em",
              }}
            >
              {workspaceCode}
            </Typography>
          )}
          <Typography
            component="h2"
            sx={{
              minWidth: 0,
              color: "text.primary",
              fontFamily:
                '"Bahnschrift Condensed", "Arial Narrow", Bahnschrift, sans-serif',
              fontSize: 19,
              fontWeight: 800,
              lineHeight: 1.05,
              letterSpacing: "0.045em",
              textTransform: "uppercase",
            }}
          >
            {workspaceLabel}
          </Typography>
          {workspaceDescription && (
            <Typography
              variant="caption"
              sx={{
                display: "block",
                mt: 0.75,
                color: "text.secondary",
                letterSpacing: "0.04em",
              }}
            >
              {workspaceDescription}
            </Typography>
          )}
        </Box>

        <Box
          component="nav"
          aria-label={ariaLabel || `${workspaceLabel} Navigation`}
          sx={{
            flex: 1,
            minHeight: 0,
            overflowY: "auto",
            px: 1.25,
            py: 1.5,
            scrollbarColor: "rgba(197, 154, 74, 0.3) transparent",
            scrollbarWidth: "thin",
          }}
        >
          {visibleSections.map((section, sectionIndex) => (
            <Box key={section.id} sx={{ mt: sectionIndex === 0 ? 0 : 2.25 }}>
              {section.label && (
                <Typography
                  variant="caption"
                  sx={{
                    display: "block",
                    px: 0.75,
                    pb: 0.7,
                    color: "primary.light",
                    letterSpacing: "0.12em",
                    textTransform: "uppercase",
                  }}
                >
                  {section.label}
                </Typography>
              )}
              <List
                disablePadding
                sx={{ borderTop: "1px solid", borderColor: "divider" }}
              >
                {section.items.map((item) => (
                  <ContextNavigationItem
                    key={item.id}
                    item={item}
                    active={item.id === activeItemId}
                    onSelect={onItemSelect}
                  />
                ))}
              </List>
            </Box>
          ))}
          {visibleSections.length === 0 && (
            <Typography
              role="status"
              variant="body2"
              sx={{ px: 1.5, py: 2, color: "text.secondary" }}
            >
              {emptyMessage}
            </Typography>
          )}
        </Box>

        {statusItems.length > 0 && (
          <Box
            sx={{
              flexShrink: 0,
              px: 1.75,
              py: 1.1,
              borderTop: "1px solid",
              borderColor: "divider",
            }}
          >
            <Stack
              direction="row"
              alignItems="center"
              spacing={0.75}
              divider={
                <Typography
                  aria-hidden
                  variant="caption"
                  sx={{ color: "text.disabled" }}
                >
                  ·
                </Typography>
              }
            >
              {statusItems.map((item) => (
                <Stack
                  key={item.id}
                  direction="row"
                  alignItems="center"
                  spacing={0.5}
                >
                  {item.color && (
                    <Box
                      aria-hidden
                      component="span"
                      sx={{ width: 6, height: 6, bgcolor: item.color }}
                    />
                  )}
                  <Typography
                    variant="caption"
                    sx={{
                      color: "text.secondary",
                      fontSize: 9,
                      letterSpacing: "0.08em",
                      textTransform: "uppercase",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {item.label}
                  </Typography>
                </Stack>
              ))}
            </Stack>
          </Box>
        )}
      </Stack>
    </Box>
  );
}
