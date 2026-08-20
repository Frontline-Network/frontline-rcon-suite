import { useEffect, useRef, useState } from "react";
import dayjs from "dayjs";
import { useGlobalStore } from "@/stores/global-state";
import { useTranslation } from "react-i18next";
import { CONNECTION_STATE } from "@/utils/connectionHealth";

const icons = {
  idle: "⚫",
  empty: "🟡",
  loading: "🟠",
  error: "🔴",
  normal: "🟢",
  ending: "🏁",
};

const numberOfBlinks = 3;
const blinkInterval = 500;

const TitleManager = () => {
  const { t } = useTranslation();
  const serverStatus = useGlobalStore((state) => state.status);
  const serverIdentity = useGlobalStore((state) => state.serverState);
  const gameState = useGlobalStore((state) => state.gameState);
  const connectionHealth = useGlobalStore((state) => state.connectionHealth);

  const [pendingTitleIcon, setPendingTitleIcon] = useState("");
  const [titleIcon, setTitleIcon] = useState(icons.loading);
  const [titleText, setTitleText] = useState(t("common.loading"));
  const titleTimeoutRef = useRef(null);

  useEffect(() => {
    let text = "";
    let icon = icons.normal;

    const serverName =
      serverIdentity?.short_name ||
      serverIdentity?.name ||
      serverStatus?.short_name ||
      serverStatus?.name ||
      t("dashboard.unknownServer");
    const crconState = connectionHealth.crcon.state;
    const gameDataState =
      connectionHealth.gameData?.state ?? CONNECTION_STATE.UNKNOWN;
    const stateLabel = (state) => t(`connectionStates.${state}`);

    if (crconState !== CONNECTION_STATE.ONLINE) {
      text = `${serverName} | CRCON · ${stateLabel(crconState)}`;
      icon =
        crconState === CONNECTION_STATE.OFFLINE ? icons.error : icons.loading;
    } else if (
      gameDataState !== CONNECTION_STATE.ONLINE ||
      !serverStatus ||
      !gameState?.current_map
    ) {
      const details = [];
      if (serverStatus?.current_players != null) {
        details.push(`(${serverStatus.current_players})`);
      }
      if (gameState?.current_map?.pretty_name) {
        details.push(gameState.current_map.pretty_name);
      }
      text = `${serverName} | ${t("sidebar.gameServer")} · ${stateLabel(
        gameDataState
      )}${details.length ? ` | ${details.join(" | ")}` : ""}`;
      icon =
        gameDataState === CONNECTION_STATE.OFFLINE
          ? icons.error
          : icons.loading;
    } else {
      const numCurrentPlayers = serverStatus.current_players;
      const mapName = gameState.current_map.pretty_name;

      if (gameState.time_remaining === 0) {
        icon = icons.idle;
      } else if (gameState.time_remaining <= 90) {
        // Not sure how to handle offensive mode
        // Lets just use a flag for now although it's not perfect
        icon = icons.ending;
      } else if (numCurrentPlayers === 0) {
        icon = icons.empty;
      }

      text = `${serverName} (${numCurrentPlayers}) | ${dayjs
        .duration(gameState.time_remaining, "seconds")
        .format("HH:mm:ss")} | ${mapName}`;
    }

    setTitleText(text);
    setPendingTitleIcon(icon);
  }, [connectionHealth, gameState, serverIdentity, serverStatus, t]);

  useEffect(() => {
    let counter = 0;
    const nextIcon = pendingTitleIcon;
    const currIcon = titleIcon;

    if (pendingTitleIcon && currIcon !== nextIcon) {
      titleTimeoutRef.current = setInterval(() => {
        counter++;
        if (counter % 2 === 1) {
          document.title = `${nextIcon} ${titleText}`;
        } else {
          document.title = `${currIcon} ${titleText}`;
        }
        if (counter === numberOfBlinks * 2) {
          counter = 0;
          setPendingTitleIcon("");
          setTitleIcon(nextIcon);
          clearInterval(titleTimeoutRef.current);
        }
      }, blinkInterval);
    } else {
      document.title = `${titleIcon} ${titleText}`;
    }

    return () => {
      titleTimeoutRef?.current && clearInterval(titleTimeoutRef.current);
    };
  }, [pendingTitleIcon, titleIcon, titleText, titleTimeoutRef]);
};

export default TitleManager;
