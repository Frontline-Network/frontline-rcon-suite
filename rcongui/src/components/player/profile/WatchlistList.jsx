import { Stack, Typography, Chip } from "@mui/material";
import dayjs from "dayjs";
import { useTranslation } from "react-i18next";

const WatchlistList = ({ watchlist }) => {
    const { t } = useTranslation();
    if (!watchlist) {
      return <Typography>{t("playerDrawer.summary.noWatchlist")}</Typography>;
    }
  
    const isActive = watchlist.is_watched;
  
    return (
      <Stack spacing={1}>
        <Typography>{watchlist.reason || t("playerDrawer.summary.noReason")}</Typography>
        <Chip
          label={isActive ? t("common.active") : t("common.disabled")}
          color={isActive ? "primary" : "error"}
          variant={isActive ? "filled" : "outlined"}
          sx={{ width: "fit-content" }}
        />
        <Typography>{t("playerDrawer.summary.visitsSince")}: {watchlist.count}</Typography>
        <Typography>{t("playerDrawer.summary.by")}: {watchlist.by}</Typography>
        {isActive && (
          <Typography>
            {t("playerDrawer.summary.modified")}: {dayjs(watchlist.modified).format("LLL")}
          </Typography>
        )}
      </Stack>
    );
  };

export default WatchlistList;
