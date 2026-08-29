import { useEffect, useMemo, useRef, useState } from "react";
import {
  Box,
  Button,
  ButtonBase,
  Checkbox,
  CircularProgress,
  Divider,
  Drawer,
  IconButton,
  Stack,
  Typography,
} from "@mui/material";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import KeyboardArrowRightRoundedIcon from "@mui/icons-material/KeyboardArrowRightRounded";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import StarRoundedIcon from "@mui/icons-material/StarRounded";
import VisibilityRoundedIcon from "@mui/icons-material/VisibilityRounded";
import { useTranslation } from "react-i18next";
import { getTeamkillRisk } from "@/utils/teamkill-risk.mjs";
import PlayerDetailPanel from "./player-detail-panel";
import { formatRoleLabel, formatSquadLabel } from "./player-display-labels";

const INITIAL_PAGE_SIZE = 40;

const teamNameColor = (team) => {
  if (team === "axis") return "error.light";
  if (team === "allies") return "info.light";
  return "text.primary";
};

const compactAssignment = (t, player) => {
  const team = t(`views.team.${player.team}`, {
    defaultValue: player.team ?? "–",
  });
  const squad = formatSquadLabel(player.unit_name ?? player.unit);
  const role = formatRoleLabel(t, player.role);
  return [team, squad, role]
    .filter((value) => value && value !== "–")
    .join(" · ");
};

const PlayerStatus = ({ player }) => {
  const { t } = useTranslation();
  const risk = getTeamkillRisk(player);
  const items = [];
  if (risk.count > 0) {
    items.push({
      key: "tk",
      label: `TK ${risk.count}`,
      icon: WarningAmberRoundedIcon,
      color: risk.level === "high" ? "error.main" : "warning.main",
    });
  }
  if (player.profile?.watchlist?.is_watched) {
    items.push({
      key: "watch",
      label: t("views.live.watched"),
      icon: VisibilityRoundedIcon,
      color: "primary.light",
    });
  }
  if (player.is_vip) {
    items.push({
      key: "vip",
      label: "VIP",
      icon: StarRoundedIcon,
      color: "warning.main",
    });
  }

  if (items.length === 0) {
    return (
      <Typography
        role="img"
        aria-label={t("views.live.noSpecialStatus")}
        color="text.disabled"
        variant="caption"
      >
        –
      </Typography>
    );
  }

  return (
    <Stack
      role="img"
      aria-label={items.map(({ label }) => label).join(", ")}
      direction="row"
      alignItems="center"
      spacing={0.25}
    >
      {items.map(({ key, label, icon: Icon, color }) => (
        <Box
          key={key}
          component="span"
          aria-hidden="true"
          title={label}
          sx={{ color, display: "inline-flex" }}
        >
          <Icon aria-hidden="true" sx={{ fontSize: 17 }} />
        </Box>
      ))}
    </Stack>
  );
};

const PlayerActionSheet = ({ player, onClose, onOpenProfile }) => {
  const { t } = useTranslation();
  const closeButtonRef = useRef(null);
  return (
    <Drawer
      anchor="bottom"
      open={Boolean(player)}
      onClose={onClose}
      hideBackdrop
      SlideProps={{ onEntered: () => closeButtonRef.current?.focus() }}
      ModalProps={{
        keepMounted: true,
        disableEnforceFocus: true,
        disableScrollLock: true,
      }}
      PaperProps={{
        role: "dialog",
        "aria-modal": "false",
        "aria-labelledby": "mobile-player-sheet-title",
      }}
      sx={(theme) => ({
        zIndex: theme.zIndex.modal,
        pointerEvents: "none",
        "& .MuiDrawer-paper": {
          backgroundImage: "none",
          bgcolor: "background.paper",
          borderTop: `1px solid ${theme.palette.primary.dark}`,
          boxShadow: theme.shadows[16],
          // Drawers render through a body-level portal and therefore cannot
          // inherit the shell's custom height variable. Keep the detail sheet
          // above the fixed 64px mobile navigation explicitly.
          bottom: "calc(64px + env(safe-area-inset-bottom, 0px))",
          maxHeight: "min(52dvh, 560px)",
          pointerEvents: "auto",
          pl: "env(safe-area-inset-left)",
          pr: "env(safe-area-inset-right)",
        },
      })}
    >
      {player ? (
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            maxHeight: "inherit",
          }}
        >
          <Stack
            direction="row"
            alignItems="center"
            spacing={1}
            sx={{
              bgcolor: "background.paper",
              minHeight: 56,
              px: 1.5,
              py: 0.75,
              position: "sticky",
              top: 0,
              zIndex: 1,
            }}
          >
            <Box sx={{ flexGrow: 1, minWidth: 0 }}>
              <Typography
                id="mobile-player-sheet-title"
                component="h2"
                noWrap
                sx={{ color: teamNameColor(player.team) }}
                variant="h6"
              >
                {player.name}
              </Typography>
              <Typography color="text.secondary" noWrap variant="caption">
                {compactAssignment(t, player)}
              </Typography>
            </Box>
            <IconButton
              ref={closeButtonRef}
              aria-label={t("common.close")}
              onClick={onClose}
              sx={{ minHeight: 44, minWidth: 44 }}
            >
              <CloseRoundedIcon />
            </IconButton>
          </Stack>
          <Divider />
          <Box sx={{ overflowY: "auto", overscrollBehavior: "contain" }}>
            <PlayerDetailPanel
              player={player}
              onActionStart={onClose}
              onOpenProfile={(selectedPlayer) => {
                onClose();
                onOpenProfile(selectedPlayer);
              }}
            />
          </Box>
        </Box>
      ) : null}
    </Drawer>
  );
};

/**
 * Compact roster for phones and narrow tablets. The first page stays bounded
 * for full servers and additional players are rendered only on demand.
 */
export default function MobilePlayerList({ table, isFetching, onOpenProfile }) {
  const { t } = useTranslation();
  const rows = table.getRowModel().rows;
  const [visibleCount, setVisibleCount] = useState(INITIAL_PAGE_SIZE);
  const [activePlayerId, setActivePlayerId] = useState(null);
  const columnFilters = table.getState().columnFilters;

  useEffect(() => {
    setVisibleCount(INITIAL_PAGE_SIZE);
  }, [rows.length, columnFilters]);

  useEffect(() => {
    if (
      activePlayerId &&
      !rows.some((row) => row.original.player_id === activePlayerId)
    ) {
      setActivePlayerId(null);
    }
  }, [activePlayerId, rows]);

  const visibleRows = rows.slice(0, visibleCount);
  const allSelected =
    visibleRows.length > 0 && visibleRows.every((row) => row.getIsSelected());
  const someSelected = visibleRows.some((row) => row.getIsSelected());
  const activePlayer = useMemo(
    () =>
      rows.find((row) => row.original.player_id === activePlayerId)?.original ??
      null,
    [activePlayerId, rows]
  );

  if (isFetching && rows.length === 0) {
    return (
      <Stack alignItems="center" sx={{ py: 5 }}>
        <CircularProgress size={26} />
      </Stack>
    );
  }

  if (rows.length === 0) {
    return (
      <Typography
        color="text.secondary"
        sx={{ p: 2, textAlign: "center" }}
        variant="body2"
      >
        {t("common.noResults")}
      </Typography>
    );
  }

  return (
    <>
      <Box component="section" aria-label={t("views.live.mobileRoster")}>
        <Stack
          direction="row"
          alignItems="center"
          sx={{
            bgcolor: "background.default",
            borderBottom: "1px solid",
            borderColor: "divider",
            minHeight: 40,
            pr: 1,
          }}
        >
          <Checkbox
            checked={allSelected}
            indeterminate={!allSelected && someSelected}
            inputProps={{ "aria-label": t("common.selectAll") }}
            onChange={(event) => {
              const selected = event.target.checked;
              visibleRows.forEach((row) => row.toggleSelected(selected));
            }}
            size="small"
            sx={{ minHeight: 44, minWidth: 44 }}
          />
          <Typography
            color="text.secondary"
            sx={{ flexGrow: 1 }}
            variant="caption"
          >
            {t("views.table.name")}
          </Typography>
          <Typography color="text.secondary" variant="caption">
            {t("views.live.mobileCombatColumn")}
          </Typography>
        </Stack>

        <Box component="ul" sx={{ listStyle: "none", m: 0, p: 0 }}>
          {visibleRows.map((row) => {
            const player = row.original;
            const assignment = compactAssignment(t, player);
            return (
              <Box
                component="li"
                key={row.id}
                data-player-row="true"
                sx={(theme) => ({
                  alignItems: "stretch",
                  bgcolor: row.getIsSelected()
                    ? "action.selected"
                    : "background.paper",
                  borderBottom: `1px solid ${theme.palette.divider}`,
                  display: "grid",
                  gridTemplateColumns: "44px minmax(0, 1fr)",
                  minHeight: 52,
                })}
              >
                <Checkbox
                  checked={row.getIsSelected()}
                  disabled={!row.getCanSelect()}
                  inputProps={{
                    "aria-label": t("common.selectPlayer", {
                      name: player.name,
                    }),
                  }}
                  onChange={row.getToggleSelectedHandler()}
                  size="small"
                  sx={{ alignSelf: "center", minHeight: 44, minWidth: 44 }}
                />
                <ButtonBase
                  aria-haspopup="dialog"
                  aria-label={t("views.live.expandPlayer", {
                    name: player.name,
                  })}
                  onClick={() => setActivePlayerId(player.player_id)}
                  sx={(theme) => ({
                    display: "grid",
                    gap: 0.75,
                    gridTemplateColumns: "minmax(0, 1fr) auto auto 44px",
                    minHeight: 52,
                    minWidth: 0,
                    textAlign: "left",
                    width: "100%",
                    "&:focus-visible": {
                      outline: `2px solid ${theme.palette.primary.main}`,
                      outlineOffset: -2,
                    },
                  })}
                >
                  <Box sx={{ minWidth: 0, py: 0.55 }}>
                    <Stack
                      direction="row"
                      alignItems="baseline"
                      spacing={0.65}
                      sx={{ minWidth: 0 }}
                    >
                      <Typography
                        noWrap
                        sx={{
                          color: teamNameColor(player.team),
                          fontWeight: 700,
                          minWidth: 0,
                        }}
                        variant="body2"
                      >
                        {player.name}
                      </Typography>
                      <Typography
                        color="text.secondary"
                        sx={{ flex: "0 0 auto" }}
                        variant="caption"
                      >
                        Lv {player.level ?? "–"}
                      </Typography>
                    </Stack>
                    <Typography
                      color="text.secondary"
                      noWrap
                      title={assignment}
                      variant="caption"
                    >
                      {assignment}
                    </Typography>
                  </Box>
                  <Typography
                    sx={{ fontVariantNumeric: "tabular-nums", fontWeight: 700 }}
                    variant="caption"
                  >
                    {player.kills ?? 0}/{player.deaths ?? 0}
                  </Typography>
                  <PlayerStatus player={player} />
                  <Box
                    aria-hidden="true"
                    sx={{
                      alignItems: "center",
                      color: "text.secondary",
                      display: "flex",
                      height: 44,
                      justifyContent: "center",
                      width: 44,
                    }}
                  >
                    <KeyboardArrowRightRoundedIcon />
                  </Box>
                </ButtonBase>
              </Box>
            );
          })}
        </Box>

        {visibleRows.length < rows.length ? (
          <Box sx={{ p: 1 }}>
            <Button
              fullWidth
              onClick={() =>
                setVisibleCount((current) =>
                  Math.min(current + INITIAL_PAGE_SIZE, rows.length)
                )
              }
              variant="outlined"
              sx={{ minHeight: 44 }}
            >
              {t("views.live.loadMorePlayers", {
                defaultValue: "Weitere Spieler laden",
              })}
            </Button>
            <Typography
              color="text.secondary"
              sx={{ display: "block", mt: 0.75, textAlign: "center" }}
              variant="caption"
            >
              {visibleRows.length} / {rows.length}
            </Typography>
          </Box>
        ) : null}
      </Box>

      <PlayerActionSheet
        player={activePlayer}
        onClose={() => setActivePlayerId(null)}
        onOpenProfile={onOpenProfile}
      />
    </>
  );
}
