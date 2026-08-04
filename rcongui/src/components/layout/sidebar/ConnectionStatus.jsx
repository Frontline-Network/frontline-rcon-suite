import { useGlobalStore } from "@/stores/global-state";
import { Box, ListItem, Stack, Tooltip, Typography } from "@mui/material";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faServer, faDesktop } from "@fortawesome/free-solid-svg-icons";
import { HIGHLIGHT } from "./utils";
import { useTranslation } from "react-i18next";

const ConnectionStatus = () => {
  const { t } = useTranslation();
  const backendConnected = useGlobalStore((state) => state.serverState);
  const gameConnected = useGlobalStore((state) => state.status);

  return (
    <>
      <ListItem disableGutters sx={{ display: "block", py: 1 }}>
        <Typography variant="caption" color="primary.light" sx={{ display: "block", mb: 0.75, textTransform: "uppercase" }}>
          {t("sidebar.connected")}
        </Typography>
        <Stack spacing={0.65}>
              <Tooltip
                enterDelay={1000}
                enterNextDelay={500}
                title={
                  gameConnected
                    ? t("sidebar.hllConnected")
                    : !backendConnected
                    ? "Connection between CRCON and HLL server is unknown"
                    : "CRCON is not connected to the HLL server"
                }
              >
                <Stack direction="row" alignItems="center" gap={1}>
                  <FontAwesomeIcon
                    icon={faServer}
                    color={
                      !gameConnected || !backendConnected
                        ? HIGHLIGHT.danger
                        : ""
                    }
                  />
                  <Typography variant="body2" sx={{ flexGrow: 1 }}>
                    {gameConnected
                      ? t("common.online")
                      : !backendConnected
                      ? t("common.unknown")
                      : t("common.offline")}
                  </Typography>
                  <Box sx={{ width: 7, height: 7, borderRadius: "50%", bgcolor: gameConnected ? "success.main" : "error.main" }} />
                </Stack>
              </Tooltip>
              <Tooltip
                enterDelay={1000}
                enterNextDelay={500}
                title={
                  backendConnected
                    ? t("sidebar.crconConnected")
                    : "The connection to CRCON has not been established"
                }
              >
                <Stack direction="row" alignItems="center" gap={1}>
                  <FontAwesomeIcon
                    icon={faDesktop}
                    color={!backendConnected ? HIGHLIGHT.danger : ""}
                  />
                  <Typography variant="body2" sx={{ flexGrow: 1 }}>
                    CRCON · {backendConnected ? t("common.online") : t("common.offline")}
                  </Typography>
                  <Box sx={{ width: 7, height: 7, borderRadius: "50%", bgcolor: backendConnected ? "success.main" : "error.main" }} />
                </Stack>
              </Tooltip>
        </Stack>
      </ListItem>
    </>
  );
};

export default ConnectionStatus;
