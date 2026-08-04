import { Stack, Typography, Chip, Divider } from "@mui/material";
import dayjs from "dayjs";
import WarningIcon from "@mui/icons-material/Warning";
import { useTranslation } from "react-i18next";

const VipList = ({ vip, otherVips }) => {
  const { t } = useTranslation();
  if (!vip && otherVips.length === 0) {
    return <Typography>{t("playerDrawer.summary.noVip")}</Typography>;
  }

  return (
    <Stack spacing={1}>
      {vip && <VipEntry vip={vip} />}
      {otherVips.length > 0 && (
        <>
          {vip && <Divider variant="middle" sx={{ my: 4 }} />}
          {otherVips.map((vip) => (
            <VipEntry key={vip.server_number} vip={vip} />
          ))}
        </>
      )}
    </Stack>
  );
};

const VipEntry = ({ vip }) => {
  const { t } = useTranslation();
  // vip.expiration is null if the VIP expiration is set indefinitely
  const expiration = dayjs(vip.expiration);
  const isActive = expiration === null ? true : expiration.isAfter(dayjs());
  // When the VIP is not created by CRCON, there is player.vip = true but no vip record entry exists
  const isNotCreatedByCrcon = vip.not_created_by_crcon;

  return (
    <Stack direction="row" alignItems="center" spacing={1}>
      <Typography variant="body2" component="span">
        {t("playerDrawer.summary.server", { number: vip.server_number })}
      </Typography>
      <div>
        <Chip
          label={isActive ? "VIP" : t("playerDrawer.summary.expired")}
          color={isActive ? "primary" : "error"}
          variant={isActive ? "filled" : "outlined"}
          icon={isNotCreatedByCrcon ? <WarningIcon /> : null}
        />
      </div>
      <Typography variant="body2" component="span">
        {isActive ? t("playerDrawer.summary.validUntil") : t("playerDrawer.summary.expiredSince")} {dayjs(vip.expiration).format("LLL")}
      </Typography>
    </Stack>
  );
};

export default VipList;
