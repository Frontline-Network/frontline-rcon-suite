import { useEffect, useRef, useState } from "react";
import dayjs from "dayjs";
import { useGlobalStore } from "@/stores/global-state";
import { gameQueryOptions } from "@/queries/game-query";
import { useQuery } from "@tanstack/react-query";
import { cmd } from "@/utils/fetchUtils";
import { useTranslation } from "react-i18next";

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
  const {
    data: gameState,
    isLoading: isGameLoading,
  } = useQuery({
    ...gameQueryOptions.state(),
    refetchInterval: 30_000,
  });

  const {
    data: serverState,
    isLoading: isServerLoading,
  } = useQuery({
    queryKey: [{ queryIdentifier: "get_status" }],
    queryFn: async () => {
      let result;
      try {
        result = await cmd.GET_GAME_SERVER_STATUS()
        useGlobalStore.setState((state) => ({ status: result }));
      } catch (error) {
        useGlobalStore.setState((state) => ({ status: null }));
      }
      return result
    },
    refetchInterval: 30_000,
    retry: 1,
  });

  const [pendingTitleIcon, setPendingTitleIcon] = useState("");
  const [titleIcon, setTitleIcon] = useState(icons.loading);
  const [titleText, setTitleText] = useState(t("common.loading"));
  const titleTimeoutRef = useRef(null);

  useEffect(() => {
    let text = "";
    let icon = icons.normal;

    if (isGameLoading || isServerLoading) {
      text = t("common.loading");
      icon = icons.loading;
    } else if (!serverState || !gameState?.current_map) {
      text = t("errors.sectionUnavailable");
      icon = icons.error;
    } else {
      const serverName = serverState.short_name;
      const numCurrentPlayers = serverState.current_players;
      const map = gameState.current_map.map;
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
  }, [serverState, gameState, isGameLoading, isServerLoading, t]);

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
