import { useGlobalStore } from "@/stores/global-state";
import { Box, ListItem, Stack, Tooltip, Typography } from "@mui/material";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faServer, faDesktop } from "@fortawesome/free-solid-svg-icons";
import { HIGHLIGHT } from "./utils";
import { useTranslation } from "react-i18next";
import { CONNECTION_STATE } from "@/utils/connectionHealth";

const stateColors = {
  [CONNECTION_STATE.ONLINE]: "success.main",
  [CONNECTION_STATE.STALE]: "warning.main",
  [CONNECTION_STATE.OFFLINE]: "error.main",
  [CONNECTION_STATE.LOADING]: "info.main",
  [CONNECTION_STATE.UNKNOWN]: "text.disabled",
};

const ConnectionStatus = () => {
  const { t } = useTranslation();
  const connectionHealth = useGlobalStore((state) => state.connectionHealth);
  const crconState = connectionHealth.crcon.state;
  const gameServerState = connectionHealth.gameServer.state;

  const stateLabel = (state) => t(`connectionStates.${state}`);

  return (
    <>
      <ListItem disableGutters sx={{ display: "block", py: 1 }}>
        <Typography
          variant="caption"
          color="primary.light"
          sx={{ display: "block", mb: 0.75, textTransform: "uppercase" }}
        >
          {t("sidebar.connected")}
        </Typography>
        <Stack spacing={0.65}>
          <Tooltip
            enterDelay={1000}
            enterNextDelay={500}
            title={t(`sidebar.gameServerState.${gameServerState}`)}
          >
            <Stack direction="row" alignItems="center" gap={1} role="status">
              <FontAwesomeIcon
                icon={faServer}
                color={
                  gameServerState === CONNECTION_STATE.OFFLINE
                    ? HIGHLIGHT.danger
                    : ""
                }
              />
              <Typography variant="body2" sx={{ flexGrow: 1 }}>
                {t("sidebar.gameServer")} · {stateLabel(gameServerState)}
              </Typography>
              <Box
                aria-hidden
                sx={{
                  width: 7,
                  height: 7,
                  borderRadius: "50%",
                  bgcolor: stateColors[gameServerState],
                }}
              />
            </Stack>
          </Tooltip>
          <Tooltip
            enterDelay={1000}
            enterNextDelay={500}
            title={t(`sidebar.crconState.${crconState}`)}
          >
            <Stack direction="row" alignItems="center" gap={1} role="status">
              <FontAwesomeIcon
                icon={faDesktop}
                color={
                  crconState === CONNECTION_STATE.OFFLINE
                    ? HIGHLIGHT.danger
                    : ""
                }
              />
              <Typography variant="body2" sx={{ flexGrow: 1 }}>
                CRCON · {stateLabel(crconState)}
              </Typography>
              <Box
                aria-hidden
                sx={{
                  width: 7,
                  height: 7,
                  borderRadius: "50%",
                  bgcolor: stateColors[crconState],
                }}
              />
            </Stack>
          </Tooltip>
        </Stack>
      </ListItem>
    </>
  );
};

export default ConnectionStatus;
