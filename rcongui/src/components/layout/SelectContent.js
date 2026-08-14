import MuiAvatar from "@mui/material/Avatar";
import Chip from "@mui/material/Chip";
import MuiListItemAvatar from "@mui/material/ListItemAvatar";
import MenuItem from "@mui/material/MenuItem";
import ListItemText from "@mui/material/ListItemText";
import ListSubheader from "@mui/material/ListSubheader";
import Select, { selectClasses } from "@mui/material/Select";
import { styled } from "@mui/material/styles";
import DevicesRoundedIcon from "@mui/icons-material/DevicesRounded";
import { useGlobalStore } from "@/stores/global-state";
import { useTranslation } from "react-i18next";

export function getServerHref(selectedServer, currentHref = window.location.href) {
  const currentUrl = new URL(currentHref);
  let targetUrl;

  if (selectedServer.link) {
    targetUrl = new URL(selectedServer.link);
  } else {
    const regex = /:(\d+)/gm;
    targetUrl = new URL(
      currentUrl.href.replace(regex, `:${selectedServer.port}`)
    );
  }

  targetUrl.pathname = currentUrl.pathname;
  targetUrl.search = currentUrl.search;
  targetUrl.hash = currentUrl.hash;
  return targetUrl.href;
}

const Avatar = styled(MuiAvatar)(({ theme }) => ({
  width: 28,
  height: 28,
  backgroundColor: theme.palette.background.paper,
  color: theme.palette.text.secondary,
  border: `1px solid ${theme.palette.divider}`,
}));

const ListItemAvatar = styled(MuiListItemAvatar)({
  minWidth: 0,
  marginRight: 12,
});

const GAME_LABELS = {
  hll: "HLL",
  hllv: "HLL: Vietnam",
};

export const getGameLabel = (game) => GAME_LABELS[game] ?? null;

export default function SelectContent() {
  const { t } = useTranslation();
  const thisServer = useGlobalStore((state) => state.serverState);
  const otherServers = useGlobalStore((state) => state.servers);

  const switchToServer = (selectedServer) => {
    window.location.assign(getServerHref(selectedServer));
  };

  const handleChange = (servers) => (event) => {
    const serverNumber = Number(event.target.value);
    const selectedServer = servers.find(
      (server) => server.server_number === serverNumber
    );
    if (!selectedServer) {
      return;
    }

    switchToServer(selectedServer);
  };

  const servers = thisServer ? [thisServer, ...otherServers] : null;

  return (
    <Select
      labelId="server-select"
      id="server-simple-select"
      value={thisServer?.server_number ?? ""}
      onChange={handleChange(servers)}
      displayEmpty
      inputProps={{ "aria-label": t("sidebar.selectServer") }}
      fullWidth
      MenuProps={{
        PaperProps: {
          sx: {
            "& .MuiMenuItem-root:not(:last-child)": {
              mb: 1,
            },
          },
        },
      }}
      sx={{
        maxHeight: 56,
        "&.MuiList-root": {
          p: "8px",
        },
        [`& .${selectClasses.select}`]: {
          display: "flex",
          alignItems: "center",
          gap: "2px",
          pl: 1,
        },
      }}
    >
      <ListSubheader sx={{ pt: 0 }}>{t("sidebar.servers")}</ListSubheader>
      {servers ? (
        servers.map((server) => {
          const gameLabel = getGameLabel(server.game);

          return (
            <MenuItem
              key={server.server_number}
              value={server.server_number}
              component="a"
              href={getServerHref(server)}
              onClick={() => switchToServer(server)}
              sx={{ minWidth: 0 }}
            >
              <ListItemAvatar>
                <Avatar alt={server.name ?? "<server_name>"}>
                  <DevicesRoundedIcon sx={{ fontSize: "1rem" }} />
                </Avatar>
              </ListItemAvatar>
              <ListItemText
                sx={{
                  minWidth: 0,
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
                primary={server.name ?? "<server_name>"}
                secondary={
                  t("sidebar.serverNumber", { number: server.server_number })
                }
              />
              {gameLabel ? (
                <Chip
                  label={gameLabel}
                  size="small"
                  color={server.game === "hllv" ? "warning" : "default"}
                  variant={server.game === "hllv" ? "filled" : "outlined"}
                  sx={{
                    flexShrink: 0,
                    height: 22,
                    ml: 1,
                    fontSize: "0.65rem",
                    fontWeight: 700,
                    letterSpacing: "0.02em",
                  }}
                />
              ) : null}
            </MenuItem>
          );
        })
      ) : (
        <MenuItem value={""}>
          <ListItemAvatar>
            <Avatar alt={"?"}>
              <DevicesRoundedIcon sx={{ fontSize: "1rem" }} />
            </Avatar>
          </ListItemAvatar>
          <ListItemText
            sx={{
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
            primary={t("common.loading")}
            secondary={"..."}
          />
        </MenuItem>
      )}
    </Select>
  );
}
