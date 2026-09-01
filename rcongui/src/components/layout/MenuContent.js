import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Stack from "@mui/material/Stack";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import { NavLink, useNavigate } from "react-router-dom";
import {
  Collapse,
  TextField,
  InputAdornment,
  Box,
  Tooltip,
} from "@mui/material";
import { useEffect, useMemo, useRef, useState } from "react";
import { useAppStore } from "@/stores/app-state";
import SearchIcon from "@mui/icons-material/Search";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/hooks/useAuth";
import { canAccessNavLink } from "@/components/Header/nav-data";

const NavigationLink = ({ to, icon, text, onClick, locked, lockedReason }) => {
  const navigate = useNavigate();
  const [lockedReasonOpen, setLockedReasonOpen] = useState(false);
  // `/apps` is an index page next to more specific app routes. Without an
  // exact match React Router also marks it active on `/apps/...`, which makes
  // two app entries look selected at the same time.
  const requiresExactMatch = to === "/" || to === "/apps";
  const button = (
    <ListItemButton
      {...(!locked && { component: NavLink, to, end: requiresExactMatch })}
      aria-disabled={locked || undefined}
      onFocus={() => locked && setLockedReasonOpen(true)}
      onBlur={() => setLockedReasonOpen(false)}
      onClick={(event) => {
        if (locked) {
          event.preventDefault();
          return;
        }

        const modifiedClick =
          event.metaKey || event.altKey || event.ctrlKey || event.shiftKey;
        const opensCurrentTab =
          event.button === 0 &&
          !modifiedClick &&
          (!event.currentTarget.target ||
            event.currentTarget.target === "_self");

        if (opensCurrentTab) {
          event.preventDefault();
          navigate(to);
        }
        onClick();
      }}
      sx={{
        borderLeft: "2px solid transparent",
        borderRadius: 0,
        minHeight: 44,
        ...(locked && {
          color: "text.disabled",
          cursor: "not-allowed",
        }),
        "&.active": {
          color: "primary.light",
          borderLeftColor: "primary.main",
          bgcolor: "action.selected",
        },
      }}
    >
      {icon && <ListItemIcon>{icon}</ListItemIcon>}
      <ListItemText primary={text} />
      {locked && (
        <LockOutlinedIcon aria-hidden fontSize="small" sx={{ ml: 1 }} />
      )}
    </ListItemButton>
  );

  return (
    <ListItem key={to} disablePadding sx={{ display: "block" }}>
      {locked ? (
        <Tooltip
          title={lockedReason}
          placement="right"
          arrow
          describeChild
          open={lockedReasonOpen}
          onOpen={() => setLockedReasonOpen(true)}
          onClose={() => setLockedReasonOpen(false)}
        >
          {button}
        </Tooltip>
      ) : (
        button
      )}
    </ListItem>
  );
};

const Group = ({
  id,
  groupName,
  icon,
  level = 1,
  open,
  forceOpen = false,
  onToggle,
  children,
}) => {
  const isOpen = forceOpen || open;

  return (
    <ListItem key={groupName} disablePadding sx={{ display: "block" }}>
      <ListItemButton
        aria-controls={`${id}-navigation-list`}
        aria-expanded={isOpen}
        onClick={onToggle}
        sx={{ minHeight: 44 }}
      >
        {icon && <ListItemIcon>{icon}</ListItemIcon>}
        <ListItemText primary={groupName} />
        {isOpen ? <ExpandLessIcon /> : <ExpandMoreIcon />}
      </ListItemButton>
      <Collapse in={isOpen} timeout={"auto"} unmountOnExit>
        <List
          id={`${id}-navigation-list`}
          dense
          sx={{ "& .MuiListItemButton-root": { pl: 2 * level } }}
          disablePadding
        >
          {children}
        </List>
      </Collapse>
    </ListItem>
  );
};

export default function MenuContent({ navigationTree, isMobile, onNavigate }) {
  const { t } = useTranslation();
  const { permissions } = useAuth();
  const toggleDrawer = useAppStore((state) => state.toggleDrawer);
  const groupOpenState = useAppStore((state) => state.groupOpenState);
  const toggleMenuGroupOpen = useAppStore((state) => state.toggleMenuGroupOpen);
  const [searchTerm, setSearchTerm] = useState("");
  const searchInputRef = useRef(null);

  const isApplePlatform = useMemo(() => {
    if (typeof navigator === "undefined") return false;
    const ua = navigator.userAgent || "";
    const uaPlatform = navigator.userAgentData?.platform || "";
    return (
      /mac|iphone|ipad|ipod/i.test(uaPlatform) ||
      /Mac OS X|Macintosh|iPhone|iPad|iPod/i.test(ua)
    );
  }, []);

  const keyHintLabel = isApplePlatform ? "⌘K" : "Ctrl+K";

  useEffect(() => {
    const onKeyDown = (e) => {
      const key = (e.key || "").toLowerCase();
      if (key !== "k") return;

      const comboPressed = isApplePlatform ? e.metaKey : e.ctrlKey;
      if (!comboPressed) return;

      e.preventDefault();
      e.stopPropagation();

      const el = searchInputRef.current;
      if (!el) return;
      el.focus();
      if (typeof el.select === "function") el.select();
    };

    window.addEventListener("keydown", onKeyDown, { capture: true });
    return () =>
      window.removeEventListener("keydown", onKeyDown, { capture: true });
  }, [isApplePlatform]);

  const toggleGroup = (groupId) => {
    toggleMenuGroupOpen(groupId);
  };

  const isGroupOpen = (groupId) => !!groupOpenState[groupId];

  const handleLinkClick = () => {
    if (isMobile) {
      // Let React Router process the link before closing and unmounting the
      // mobile drawer. Closing synchronously can cancel client-side routing.
      window.requestAnimationFrame(() => (onNavigate ?? toggleDrawer)());
    }
  };

  // Filter navigation tree based on search term
  const getLabel = (item) =>
    item.translationKey ? t(item.translationKey) : item.name;

  const filterNavigationTree = (tree, searchTerm) => {
    if (!searchTerm.trim()) {
      return tree;
    }

    const lowerSearchTerm = searchTerm.toLowerCase();

    return tree
      .map((group) => {
        // Check if group has a name (it's a group)
        if ("name" in group) {
          const groupNameMatches = getLabel(group)
            .toLowerCase()
            .includes(lowerSearchTerm);

          // Filter links that match
          const matchingLinks = group.links.filter((link) =>
            getLabel(link).toLowerCase().includes(lowerSearchTerm)
          );

          // If group name matches, show all links; if only links match, show group with filtered links
          if (groupNameMatches || matchingLinks.length > 0) {
            return {
              ...group,
              links: groupNameMatches ? group.links : matchingLinks,
            };
          }
          return null;
        } else {
          // It's a link without a group
          const matchingLinks = group.links.filter((link) =>
            getLabel(link).toLowerCase().includes(lowerSearchTerm)
          );

          if (matchingLinks.length > 0) {
            return {
              ...group,
              links: matchingLinks,
            };
          }
          return null;
        }
      })
      .filter((group) => group !== null);
  };

  const filteredTree = filterNavigationTree(navigationTree, searchTerm);

  return (
    <Stack
      sx={{
        flexGrow: 1,
        p: 1,
        overflow: "hidden",
      }}
    >
      <Stack direction={"row"} alignItems={"start"} spacing={0.5}>
        <TextField
          size="small"
          fullWidth
          placeholder={t("navigation.search")}
          inputProps={{ "aria-label": t("navigation.search") }}
          name="crcon-search"
          inputRef={searchInputRef}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          sx={{ mb: 1 }}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
              endAdornment: !isMobile ? (
                <InputAdornment position="end">
                  <Box
                    aria-hidden
                    onMouseDown={(e) => {
                      // Keep focus in the input when clicking the hint.
                      e.preventDefault();
                      searchInputRef.current?.focus?.();
                    }}
                    sx={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 0.75,
                      px: 0.75,
                      py: 0.25,
                      borderRadius: 1,
                      border: "1px solid",
                      borderColor: "divider",
                      bgcolor: (theme) => theme.palette.background.paper,
                      color: "text.secondary",
                      fontSize: 12,
                      lineHeight: 1,
                      fontFamily:
                        'ui-monospace, SFMono-Regular, SF Mono, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
                      letterSpacing: 0.2,
                      userSelect: "none",
                      boxShadow: (theme) =>
                        `inset 0 1px 0 ${theme.palette.action.hover}, inset 0 -1px 0 ${theme.palette.action.selected}`,
                    }}
                  >
                    {keyHintLabel}
                  </Box>
                </InputAdornment>
              ) : null,
            },
          }}
        />
      </Stack>
      <List dense sx={{ overflowY: "auto", scrollbarWidth: "none" }}>
        {filteredTree
          .filter((group) => !("name" in group))
          .map((group) =>
            group.links.map((link) => (
              <NavigationLink
                key={link.to}
                to={link.to}
                text={getLabel(link)}
                icon={link.icon}
                onClick={handleLinkClick}
                locked={!canAccessNavLink(link, permissions)}
                lockedReason={t("navigation.permissionMissing")}
              />
            ))
          )}

        {filteredTree
          .filter((group) => "name" in group)
          .map((group) => (
            <Group
              key={group.id}
              id={group.id}
              groupName={getLabel(group)}
              icon={group.icon}
              open={isGroupOpen(group.id)}
              forceOpen={!!searchTerm.trim()}
              onToggle={() => toggleGroup(group.id)}
            >
              {group.links.map((link) => (
                <NavigationLink
                  key={link.to}
                  to={link.to}
                  text={getLabel(link)}
                  icon={link.icon}
                  onClick={handleLinkClick}
                  locked={!canAccessNavLink(link, permissions)}
                  lockedReason={t("navigation.permissionMissing")}
                />
              ))}
            </Group>
          ))}
      </List>
    </Stack>
  );
}
