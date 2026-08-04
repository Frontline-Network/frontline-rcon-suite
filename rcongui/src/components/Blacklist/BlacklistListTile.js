import {
  IconButton,
  InputLabel,
  Paper,
  Tooltip,
  Typography,
} from "@mui/material";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import Grid from "@mui/material/Grid2";
import {Fragment} from "react";
import { useTranslation } from "react-i18next";


const BlacklistListTile = ({
  blacklist,
  servers,
  onEdit,
  onDelete,
}) => {
  const { t } = useTranslation();

  function serverNumberToName(serverNumber) {
    return servers[serverNumber] || serverNumber.toString();
  }

  return (
    (<Paper>
      <Grid container
        justifyContent="space-between"
        alignItems="center"
        spacing={2}
        style={{paddingLeft: 18}}
      >
        <Grid>
          <Typography variant="h6" color="textSecondary">#{blacklist.id}</Typography>
        </Grid>
        <Grid size={2}>
          <InputLabel align="left">{t("records.blacklists.listName")}</InputLabel>
          <Typography align="left">
            {blacklist.name}
          </Typography>
        </Grid>

        <Grid size={6}>
          <InputLabel align="left">{t("records.blacklists.servers")}</InputLabel>
          {
            blacklist.servers === null
            ? <Typography align="left">{t("records.blacklists.allServers")}</Typography>
            : blacklist.servers.length === 0
            ? <Typography align="left">{t("records.blacklists.noServers")}</Typography>
            : <Fragment>
              {blacklist.servers.map((num) => (
                <Typography key={num} align="left" noWrap>
                  {serverNumberToName(num)}
                </Typography>
              ))}
            </Fragment>
          }
        </Grid>
        
        <Grid size={2}>
          <InputLabel align="left">{t("records.blacklists.syncMethod")}</InputLabel>
          <Typography align="left">{t(`records.blacklists.syncMethods.${blacklist.sync}`)}</Typography>
        </Grid>
        
        <Grid>
          <Tooltip title={t("common.edit")}>
            <IconButton onClick={() => onEdit(blacklist)} size="large">
              <EditIcon/>
            </IconButton>
          </Tooltip>
          <Tooltip title={t("common.delete")}>
            <span>
              <IconButton
                onClick={() => onDelete(blacklist)}
                disabled={blacklist.id === 0}
                size="large">
                <DeleteIcon/>
              </IconButton>
            </span>
          </Tooltip>
        </Grid>
      </Grid>
    </Paper>)
  );
}

export default BlacklistListTile;
