import { useQuery } from "@tanstack/react-query";
import { cmd } from "@/utils/fetchUtils";
import {
  Card,
  CardHeader,
  CardContent,
  Typography,
  Box,
  Grid2 as Grid,
  Stack,
  Tooltip,
} from "@mui/material";
import { Link } from "react-router-dom";
import { useMemo } from "react";
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CancelIcon from '@mui/icons-material/Cancel';
import WebhookIcon from '@mui/icons-material/Webhook';
import { useTranslation } from "react-i18next";
import { isFakeMode } from "@/mirage/demo-data";

const loadConfig = (request, demo) =>
  isFakeMode() ? Promise.resolve(demo) : request();

const AutomodsCard = () => {
  const { t } = useTranslation();
  // Fetch all automod settings
  const { data: seeding } = useQuery({
    queryKey: ["settings", "automods", "seeding"],
    queryFn: async () => {
      const result = await loadConfig(cmd.GET_SEEDING_CONFIG, { enabled: true, discord_webhook_url: "https://discord.example/frontline" });
      return result;
    },
  });

  const { data: noLeader } = useQuery({
    queryKey: ["settings", "automods", "no-leader"],
    queryFn: async () => {
      const result = await loadConfig(cmd.GET_NO_LEADER_CONFIG, { enabled: true });
      return result;
    },
  });

  const { data: noSoloTank } = useQuery({
    queryKey: ["settings", "automods", "no-solo-tank"],
    queryFn: async () => {
      const result = await loadConfig(cmd.GET_NO_SOLO_TANK_CONFIG, { enabled: false });
      return result;
    },
  });

  const { data: level } = useQuery({
    queryKey: ["settings", "automods", "level"],
    queryFn: async () => {
      const result = await loadConfig(cmd.GET_LEVEL_CONFIG, { enabled: true });
      return result;
    },
  });

  const { data: nameKicks } = useQuery({
    queryKey: ["settings", "others", "name-kicks"],
    queryFn: async () => {
      const result = await loadConfig(cmd.GET_NAME_KICKS_CONFIG, { enabled: false });
      return result;
    },
  });

  const { data: vacBans } = useQuery({
    queryKey: ["settings", "others", "vac-bans"],
    queryFn: async () => {
      const result = await loadConfig(cmd.GET_VAC_CONFIG, { enabled: true });
      return result;
    },
  });

  const { data: seedingReward } = useQuery({
    queryKey: ["settings", "automods", "seeding-reward"],
    queryFn: async () => {
      const result = await loadConfig(cmd.GET_SEEDING_REWARD_CONFIG, { enabled: true });
      return result;
    },
  });

  const { data: chatCommands } = useQuery({
    queryKey: ["settings", "others", "chat-commands"],
    queryFn: async () => {
      const result = await loadConfig(cmd.GET_CHAT_COMMANDS_CONFIG, { enabled: true });
      return result;
    },
  });

  const { data: rconCommands } = useQuery({
    queryKey: ["settings", "others", "rcon-commands"],
    queryFn: async () => {
      const result = await loadConfig(cmd.GET_RCON_CHAT_COMMANDS_CONFIG, { enabled: false });
      return result;
    },
  });

  const automodSettings = [
    { 
      key: 'seeding', 
      label: t('navigation.links.seeding'),
      value: seeding?.enabled,
      webhook: seeding?.discord_webhook_url,
      category: 'Automods',
      path: '/settings/automods/seeding'
    },
    { 
      key: 'seeding_reward', 
      label: t('navigation.links.seedVip'),
      value: seedingReward?.enabled,
      webhook: seedingReward?.discord_webhook_url,
      category: 'Others',
      path: '/settings/others/seed-vip'
    },
    { 
      key: 'no_leader', 
      label: t('navigation.links.noLeader'),
      value: noLeader?.enabled,
      webhook: noLeader?.discord_webhook_url,
      category: 'Automods',
      path: '/settings/automods/no-leader'
    },
    { 
      key: 'no_solo_tank', 
      label: t('navigation.links.noSoloTank'),
      value: noSoloTank?.enabled,
      webhook: noSoloTank?.discord_webhook_url,
      category: 'Automods',
      path: '/settings/automods/no-solo-tank'
    },
    { 
      key: 'level', 
      label: t('navigation.links.level'),
      value: level?.enabled,
      webhook: level?.discord_webhook_url,
      category: 'Automods',
      path: '/settings/automods/level'
    },
    { 
      key: 'chat_commands', 
      label: t('navigation.links.chatCommands'),
      value: chatCommands?.enabled,
      webhook: chatCommands?.discord_webhook_url,
      category: 'Others',
      path: '/settings/others/chat-commands'
    },
    { 
      key: 'rcon_commands', 
      label: t('navigation.links.rconCommands'),
      value: rconCommands?.enabled,
      webhook: rconCommands?.discord_webhook_url,
      category: 'Others',
      path: '/settings/others/rcon-chat-commands'
    },
  ];

  // Group automods by their status (enabled/disabled)
  const groupedAutomods = useMemo(() => {
    const groups = {
      ENABLED: [],
      DISABLED: []
    };

    automodSettings.forEach(setting => {
      const status = setting.value ? 'ENABLED' : 'DISABLED';
      groups[status].push(setting);
    });

    return groups;
  }, [automodSettings]);

  // Helper function to get status color
  const getStatusColor = (status) => {
    switch (status) {
      case 'ENABLED':
        return (theme) => theme.palette.mode === 'dark' ? '#4caf50' : '#2e7d32';
      case 'DISABLED':
        return (theme) => theme.palette.mode === 'dark' ? '#f44336' : '#d32f2f';
      default:
        return 'text.secondary';
    }
  };

  // Helper function to get status icon
  const StatusIcon = ({ status }) => {
    switch (status) {
      case 'ENABLED':
        return <CheckCircleIcon sx={{ fontSize: '1.2rem', color: getStatusColor(status) }} />;
      case 'DISABLED':
        return <CancelIcon sx={{ fontSize: '1.2rem', color: getStatusColor(status) }} />;
      default:
        return null;
    }
  };

  const AutomodItem = ({ automod }) => (
    <Box
      component={Link}
      to={automod.path}
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 0.75,
        py: 0.25,
        px: 0.5,
        color: 'text.primary',
        textDecoration: 'none',
        borderRadius: 1,
        '&:hover': {
          bgcolor: 'action.hover'
        }
      }}
    >
      <StatusIcon status={automod.value ? 'ENABLED' : 'DISABLED'} />
      <Typography variant="body2" sx={{ fontWeight: 500, flexGrow: 1 }}>
        {automod.label}
      </Typography>
      {automod.webhook && (
        <Tooltip title={t("common.webhookConfigured")}>
          <WebhookIcon sx={{ fontSize: '1rem', color: 'primary.main' }} />
        </Tooltip>
      )}
    </Box>
  );

  const AutomodGroup = ({ status, automods }) => (
    <Box>
      <Typography 
        variant="subtitle2" 
        color="text.secondary" 
        sx={{ 
          mb: 0.5,
          display: 'flex',
          alignItems: 'center',
          gap: 0.5 
        }}
      >
        <StatusIcon status={status} />
        {status === "ENABLED" ? t("dashboard.enabled") : t("common.disabled")} ({automods.length})
      </Typography>
      <Stack spacing={0.25}>
        {automods.map(automod => (
          <AutomodItem key={automod.key} automod={automod} />
        ))}
      </Stack>
    </Box>
  );

  return (
    <Card sx={{ height: "100%" }}>
      <CardHeader title={t("dashboard.automodsServices")} />
      <CardContent>
        <Grid container spacing={2}>
          {Object.entries(groupedAutomods).map(([status, automodsList]) => (
            <Grid key={status} size={{ xs: 12, md: 6 }}>
              <AutomodGroup status={status} automods={automodsList} />
            </Grid>
          ))}
        </Grid>
      </CardContent>
    </Card>
  );
};

export default AutomodsCard;
