import { createElement, isValidElement, useState } from "react";
import {
  Box,
  InputAdornment,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import SearchRoundedIcon from "@mui/icons-material/SearchRounded";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import { alpha } from "@mui/material/styles";
import { NavLink } from "react-router-dom";
import {
  getContextNavigationSurface,
  getNavigationControlSurface,
} from "./navigation-surfaces";

export const CONTEXT_NAVIGATION_PANEL_WIDTH = 276;

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
        minHeight: 42,
        px: 1.5,
        py: 0.75,
        borderRadius: 0,
        borderLeft: "3px solid",
        borderLeftColor: active ? "primary.main" : "transparent",
        color: active ? "primary.light" : "text.secondary",
        bgcolor: active
          ? alpha(theme.palette.primary.main, 0.13)
          : "transparent",
        cursor: locked ? "not-allowed" : "pointer",
        "&:hover": {
          color: active ? "primary.light" : "text.primary",
          bgcolor: active
            ? alpha(theme.palette.primary.main, 0.17)
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
        <ListItemIcon sx={{ minWidth: 32, color: "inherit" }}>
          {renderIcon(item.icon)}
        </ListItemIcon>
      )}
      <ListItemText
        primary={item.label}
        secondary={item.description}
        primaryTypographyProps={{
          fontSize: 13,
          fontWeight: active ? 700 : 500,
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
        <Tooltip title={item.lockedReason || ""} placement="right" arrow>
          {button}
        </Tooltip>
      ) : (
        button
      )}
    </ListItem>
  );
}

/**
 * Route-agnostic second navigation level for the active workspace. Sections
 * and item ids are supplied by the caller so permissions and routing remain
 * outside this visual component.
 */
export default function ContextNavigationPanel({
  workspaceLabel,
  workspaceCode,
  workspaceDescription,
  sections = [],
  activeItemId,
  onItemSelect,
  ariaLabel,
  width = CONTEXT_NAVIGATION_PANEL_WIDTH,
  searchValue,
  defaultSearchValue = "",
  onSearchChange,
  searchPlaceholder = "Navigation durchsuchen …",
  emptyMessage = "No matching pages found.",
  searchHint,
  searchInputRef,
  showSearch = true,
  topSlot,
  headerSlot,
  footerSlot,
  id = "desktop-navigation-panel",
  presentation = "persistent",
  onKeyDown,
}) {
  const [internalSearchValue, setInternalSearchValue] =
    useState(defaultSearchValue);
  const resolvedSearchValue = searchValue ?? internalSearchValue;
  const normalizedQuery = resolvedSearchValue.trim().toLocaleLowerCase();
  const visibleSections = sections
    .map((section) => ({
      ...section,
      items: normalizedQuery
        ? section.items.filter((item) =>
            `${item.label} ${item.description || ""}`
              .toLocaleLowerCase()
              .includes(normalizedQuery)
          )
        : section.items,
    }))
    .filter((section) => section.items.length > 0);

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
        {topSlot && (
          <Box
            sx={{
              flexShrink: 0,
              borderBottom: "1px solid",
              borderColor: "divider",
            }}
          >
            {topSlot}
          </Box>
        )}
        <Box
          sx={{
            px: 2,
            pt: 2,
            pb: 1.5,
            borderBottom: "1px solid",
            borderColor: "divider",
          }}
        >
          <Stack direction="row" alignItems="baseline" spacing={1}>
            {workspaceCode && (
              <Typography
                variant="caption"
                sx={{ color: "primary.main", letterSpacing: "0.16em" }}
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
                fontSize: 18,
                fontWeight: 800,
                lineHeight: 1.1,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
              }}
            >
              {workspaceLabel}
            </Typography>
          </Stack>
          {workspaceDescription && (
            <Typography
              variant="caption"
              sx={{ display: "block", mt: 0.75, color: "text.secondary" }}
            >
              {workspaceDescription}
            </Typography>
          )}
          {headerSlot && <Box sx={{ mt: 1.25 }}>{headerSlot}</Box>}
        </Box>

        {showSearch && (
          <Box sx={{ px: 1.25, pt: 1.25 }}>
            <TextField
              value={resolvedSearchValue}
              onChange={(event) => {
                if (searchValue === undefined) {
                  setInternalSearchValue(event.target.value);
                }
                onSearchChange?.(event.target.value);
              }}
              placeholder={searchPlaceholder}
              inputProps={{ "aria-label": searchPlaceholder }}
              inputRef={searchInputRef}
              size="small"
              fullWidth
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchRoundedIcon sx={{ fontSize: 18 }} />
                    </InputAdornment>
                  ),
                  endAdornment: searchHint ? (
                    <InputAdornment position="end">
                      <Typography
                        component="kbd"
                        variant="caption"
                        sx={{
                          px: 0.6,
                          py: 0.25,
                          border: "1px solid",
                          borderColor: "divider",
                          color: "text.secondary",
                          fontFamily: "monospace",
                          lineHeight: 1,
                        }}
                      >
                        {searchHint}
                      </Typography>
                    </InputAdornment>
                  ) : null,
                },
              }}
              sx={{
                "& .MuiOutlinedInput-root": {
                  minHeight: 40,
                  borderRadius: 0,
                  bgcolor: getNavigationControlSurface,
                },
              }}
            />
          </Box>
        )}

        <Box
          component="nav"
          aria-label={ariaLabel || `${workspaceLabel} Navigation`}
          sx={{
            flex: 1,
            minHeight: 0,
            overflowY: "auto",
            px: 1,
            py: 1.25,
            scrollbarColor: "rgba(197, 154, 74, 0.3) transparent",
            scrollbarWidth: "thin",
          }}
        >
          {visibleSections.map((section, sectionIndex) => (
            <Box key={section.id} sx={{ mt: sectionIndex === 0 ? 0 : 2 }}>
              {section.label && (
                <Typography
                  variant="caption"
                  sx={{
                    display: "block",
                    px: 1.5,
                    pb: 0.65,
                    color: "primary.light",
                    textTransform: "uppercase",
                  }}
                >
                  {section.label}
                </Typography>
              )}
              <List disablePadding>
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

        {footerSlot && (
          <Box
            sx={{
              flexShrink: 0,
              p: 1.25,
              borderTop: "1px solid",
              borderColor: "divider",
            }}
          >
            {footerSlot}
          </Box>
        )}
      </Stack>
    </Box>
  );
}
