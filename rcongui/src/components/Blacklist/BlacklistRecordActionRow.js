import { ButtonGroup, Button } from "@mui/material";
import Tooltip from "@mui/material/Tooltip";
import EditIcon from "@mui/icons-material/Edit";
import TimerOffIcon from "@mui/icons-material/TimerOff";
import DeleteIcon from "@mui/icons-material/Delete";
import Grid from "@mui/material/Grid2";
import { useTranslation } from "react-i18next";


const BlacklistRecordActionRow = ({
  isExpired,
  onEdit,
  onExpire,
  onDelete,
}) => {
  const { t } = useTranslation();
  return (
    (<Grid container justifyContent="center">
      <Grid>
        <ButtonGroup size="small" variant="text">
          <Button onClick={onEdit} aria-label={t("records.blacklists.editRecord")}>
            <Tooltip
              title={t("records.blacklists.editRecord")}
              arrow
            >
              <EditIcon size="small" />
            </Tooltip>
          </Button>

          <Button disabled={isExpired} onClick={onExpire} aria-label={t("records.blacklists.expireRecord")}>
            <Tooltip title={t("records.blacklists.expireRecord")} arrow>
              <TimerOffIcon size="small" />
            </Tooltip>
          </Button>

          <Button onClick={onDelete} aria-label={t("records.blacklists.deleteRecord")}>
            <Tooltip title={t("records.blacklists.deleteRecord")} arrow>
              <DeleteIcon size="small" />
            </Tooltip>
          </Button>
        </ButtonGroup>
      </Grid>
    </Grid>)
  );
};

export default BlacklistRecordActionRow;
