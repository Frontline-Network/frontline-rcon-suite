import { useCallback, useMemo, useState } from "react";
import { ActionMenu } from "@/features/player-action/ActionMenu";
import { generatePlayerActions } from "@/features/player-action/actions";

const ONLINE_PLAYER_ACTIONS = generatePlayerActions({
  multiAction: false,
  onlineAction: true,
});
const HISTORICAL_PLAYER_ACTIONS = generatePlayerActions({
  multiAction: false,
  onlineAction: false,
});

export const GAME_LOG_PLAYER_ACTION_MENU_ID = "game-log-player-actions-menu";

export const useGameLogPlayerActionMenu = () => {
  const [state, setState] = useState({
    anchorEl: null,
    onlineAction: false,
    player: null,
    triggerKey: null,
  });

  const openPlayerActionMenu = useCallback(
    (anchorEl, player, { onlineAction = false, triggerKey = null } = {}) => {
      setState({ anchorEl, onlineAction, player, triggerKey });
    },
    []
  );
  const setAnchorEl = useCallback((anchorEl) => {
    setState((current) => ({ ...current, anchorEl }));
  }, []);
  const tableMeta = useMemo(
    () => ({
      activePlayerActionKey: state.anchorEl ? state.triggerKey : null,
      openPlayerActionMenu,
    }),
    [openPlayerActionMenu, state.anchorEl, state.triggerKey]
  );

  return { setAnchorEl, state, tableMeta };
};

export const GameLogPlayerActionMenu = ({ controller }) => {
  const { setAnchorEl, state } = controller;
  if (!state.player) return null;

  return (
    <ActionMenu
      actions={
        state.onlineAction ? ONLINE_PLAYER_ACTIONS : HISTORICAL_PLAYER_ACTIONS
      }
      recipients={state.player}
      withProfile
      anchorEl={state.anchorEl}
      setAnchorEl={setAnchorEl}
      menuId={GAME_LOG_PLAYER_ACTION_MENU_ID}
    />
  );
};
