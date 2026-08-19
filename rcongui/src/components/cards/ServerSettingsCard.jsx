import { useQuery } from "@tanstack/react-query";
import { cmd } from "@/utils/fetchUtils";
import {
  Card,
  CardHeader,
  CardContent,
  IconButton,
  Typography,
  Box,
  Grid2 as Grid,
} from "@mui/material";
import { Link } from "react-router-dom";
import SettingsIcon from '@mui/icons-material/Settings';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import { useTranslation } from "react-i18next";
import { demoServerSettings, isFakeMode } from "@/mirage/demo-data";

const ServerSettingsCard = () => {
  const { t } = useTranslation();
  const { data: settings } = useQuery({
    queryKey: ["settings", "server"],
    queryFn: async () => {
      const result = isFakeMode()
        ? demoServerSettings
        : await cmd.GET_SERVER_SETTINGS();
      return result;
    },
  });

  const booleanSettings = [
    { key: 'autobalance_enabled', label: t('serverSettings.teamAutobalance') },
    { key: 'votekick_enabled', label: t('serverSettings.votekick') },
  ];

  const numericSettings = [
    { key: 'team_switch_cooldown', label: t('serverSettings.switchCooldown'), unit: 'min' },
    { key: 'autobalance_threshold', label: t('serverSettings.threshold'), unit: t('serverSettings.playersUnit') },
    { key: 'idle_autokick_time', label: t('serverSettings.idleKick'), unit: 'min' },
    { key: 'max_ping_autokick', label: t('serverSettings.maxPing'), unit: 'ms' },
    { key: 'queue_length', label: t('serverSettings.queue'), unit: t('serverSettings.playersUnit') },
    { key: 'vip_slots_num', label: t('serverSettings.vipSlots'), unit: t('serverSettings.slotsUnit') },
  ];

  return (
    <Card sx={{ height: "100%" }}>
      <CardHeader 
        title={t("dashboard.serverSettings")}
        action={
          <IconButton 
            component={Link} 
            to="/settings"
            size="small"
            aria-label={t("dashboard.openServerSettings")}
            sx={{ color: 'text.secondary' }}
          >
            <SettingsIcon />
          </IconButton>
        }
      />
      <CardContent>
        <Grid container spacing={2}>
          {/* Boolean Settings */}
          <Grid size={12}>
            <Box sx={{ 
              display: 'flex', 
              gap: 2,
              mb: 1
            }}>
              {booleanSettings.map(({ key, label }) => (
                <Box 
                  key={key}
                  sx={{ 
                    display: 'flex',
                    alignItems: 'center',
                    gap: 0.5
                  }}
                >
                  <Typography variant="body2" color="text.secondary">
                    {label}:
                  </Typography>
                  {settings?.[key] ? (
                    <CheckCircleIcon 
                      sx={{ 
                        color: 'success.main',
                        fontSize: '1.2rem'
                      }} 
                    />
                  ) : (
                    <CancelIcon 
                      sx={{ 
                        color: 'error.main',
                        fontSize: '1.2rem'
                      }} 
                    />
                  )}
                </Box>
              ))}
            </Box>
          </Grid>

          {/* Numeric Settings */}
          {numericSettings.map(({ key, label, unit }) => (
            <Grid size={{ xs: 12 }} key={key}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <Typography variant="body2" color="text.secondary">
                  {label}:
                </Typography>
                <Typography 
                  variant="body2" 
                  sx={{ 
                    fontWeight: 500,
                    color: settings?.[key] === 0 ? 'text.disabled' : 'text.primary'
                  }}
                >
                    {settings?.[key] === 0 ? t('common.disabled') : `${settings?.[key]} ${unit}`}
                </Typography>
              </Box>
            </Grid>
          ))}
        </Grid>
      </CardContent>
    </Card>
  );
};

export default ServerSettingsCard;
