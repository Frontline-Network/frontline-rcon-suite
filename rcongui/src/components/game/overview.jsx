import { GroupsRounded, MapRounded, TimerOutlined } from '@mui/icons-material'
import { Box, Typography, alpha, styled } from '@mui/material'
import { useTranslation } from 'react-i18next'
import { ArrowsContainer, OffensiveArrows, WarfareArrows } from './shapes'
import { useThemedImages } from '@/hooks/useThemedImages'

const TEAM_COLORS = {
  allies: '#6f9ea3',
  axis: '#c55f51',
}

const OverviewShell = styled(Box)(({ theme }) => ({
  position: 'relative',
  overflow: 'hidden',
  width: '100%',
  padding: theme.spacing(1.5, 2, 2),
  borderTop: `1px solid ${alpha(theme.palette.primary.main, 0.28)}`,
  borderBottom: `1px solid ${alpha(theme.palette.primary.main, 0.2)}`,
  background: `linear-gradient(100deg, ${alpha(theme.palette.background.paper, 0.98)} 0%, ${alpha(theme.palette.primary.dark, 0.14)} 50%, ${alpha(theme.palette.background.paper, 0.98)} 100%)`,
  boxShadow: `inset 0 1px 0 ${alpha(theme.palette.primary.light, 0.08)}`,
  '&::before': {
    content: '""',
    position: 'absolute',
    inset: 0,
    pointerEvents: 'none',
    opacity: 0.28,
    backgroundImage: `linear-gradient(90deg, transparent 0%, ${alpha(theme.palette.primary.main, 0.14)} 50%, transparent 100%)`,
  },
  [theme.breakpoints.down('sm')]: {
    padding: theme.spacing(1.25, 1.25, 1.5),
  },
}))

const TeamIdentity = styled(Box, {
  shouldForwardProp: (prop) => prop !== 'team',
})(({ team, theme }) => ({
  display: 'grid',
  gridTemplateColumns: 'auto minmax(0, 1fr)',
  alignItems: 'center',
  gap: theme.spacing(1.25),
  minWidth: 0,
  padding: theme.spacing(1, 1.25),
  border: `1px solid ${alpha(TEAM_COLORS[team], 0.32)}`,
  borderLeft: `3px solid ${TEAM_COLORS[team]}`,
  borderRadius: theme.shape.borderRadius,
  backgroundColor: alpha(TEAM_COLORS[team], 0.07),
  boxShadow: `inset 0 1px 0 ${alpha(TEAM_COLORS[team], 0.1)}`,
  [theme.breakpoints.down('sm')]: {
    gap: theme.spacing(0.75),
    padding: theme.spacing(0.75, 1),
  },
}))

const TeamImage = styled('img')(({ theme }) => ({
  display: 'block',
  width: 48,
  height: 48,
  objectFit: 'contain',
  filter: `drop-shadow(0 3px 8px ${alpha(theme.palette.common.black, 0.42)})`,
  [theme.breakpoints.down('sm')]: {
    width: 38,
    height: 38,
  },
}))

const MetaItem = ({ icon, children }) => (
  <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5, color: 'text.secondary' }}>
    {icon}
    <Typography variant="caption" component="span" sx={{ color: 'inherit', lineHeight: 1.2 }}>
      {children}
    </Typography>
  </Box>
)

const TeamPanel = ({ team, faction, count, imageSrc, label, playersLabel }) => (
  <TeamIdentity team={team}>
    <TeamImage src={imageSrc} alt={faction.team} />
    <Box sx={{ minWidth: 0 }}>
      <Typography
        variant="caption"
        sx={{ display: 'block', color: TEAM_COLORS[team], lineHeight: 1.1, mb: 0.25 }}
      >
        {label}
      </Typography>
      <Typography variant="h6" noWrap sx={{ fontSize: { xs: '0.85rem', sm: '1rem' }, lineHeight: 1.1 }}>
        {faction.team}
      </Typography>
      <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 0.65, mt: 0.5 }}>
        <Typography component="span" variant="h4" sx={{ color: TEAM_COLORS[team], fontSize: { xs: '1.35rem', sm: '1.7rem' }, lineHeight: 1 }}>
          {count ?? '–'}
        </Typography>
        <Typography component="span" variant="caption" sx={{ color: 'text.secondary' }}>
          {playersLabel}
        </Typography>
      </Box>
    </Box>
  </TeamIdentity>
)

export default function GameOverview({
  map,
  time,
  allies,
  axis,
  mode,
  mapName,
  axisCount,
  alliesCount,
  score,
}) {
  const { t } = useTranslation()
  const themedImg = useThemedImages()
  const gameMode = t(`views.team.gameModes.${mode}`, { defaultValue: mode })
  const attackers = map?.attackers ? t(`views.team.factions.${map.attackers}`, { defaultValue: map.attackers }) : null
  const displayArrows = () => {
    if (score.allies === undefined || score.axis === undefined) return null

    return (
      <ArrowsContainer>
        {mode === 'offensive' && <OffensiveArrows score={score} map={map} />}
        {mode === 'warfare' && <WarfareArrows score={score} />}
      </ArrowsContainer>
    )
  }

  return (
    <OverviewShell component="section" aria-label={t('views.team.battleOverview')}>
      <Box sx={{ position: 'relative' }}>
        {displayArrows()}

        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: { xs: '1fr 1fr', md: 'minmax(0, 1fr) minmax(150px, 0.5fr) minmax(0, 1fr)' },
            alignItems: 'center',
            gap: { xs: 1, sm: 1.5, md: 2 },
          }}
        >
          <TeamPanel
            team="allies"
            faction={allies}
            count={alliesCount}
            imageSrc={themedImg.getFactionIconSrc(allies.name)}
            label={t('views.team.allies')}
            playersLabel={t('views.team.players')}
          />

          <Box
            sx={{
              gridColumn: { xs: '1 / -1', md: 'auto' },
              gridRow: { xs: 1, md: 'auto' },
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              minWidth: 0,
              px: { xs: 0.5, md: 1 },
              py: { xs: 0.25, md: 0.5 },
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, color: 'text.secondary', mb: 0.25 }}>
              <TimerOutlined sx={{ fontSize: '0.95rem' }} />
              <Typography variant="caption">{time}</Typography>
            </Box>
            <Typography
              variant="h2"
              sx={{
                color: 'text.primary',
                fontSize: { xs: '2.25rem', sm: '2.75rem', md: '3.35rem' },
                lineHeight: 0.95,
                whiteSpace: 'nowrap',
                textShadow: '0 3px 16px rgba(0, 0, 0, 0.65)',
              }}
            >
              {score.allies ?? '?'} <Box component="span" sx={{ color: 'primary.main', mx: 0.2 }}>:</Box> {score.axis ?? '?'}
            </Typography>
            <Typography variant="caption" sx={{ color: 'primary.light', mt: 0.5 }}>
              {t('views.team.liveScore')}
            </Typography>
          </Box>

          <TeamPanel
            team="axis"
            faction={axis}
            count={axisCount}
            imageSrc={themedImg.getFactionIconSrc(axis.name)}
            label={t('views.team.axis')}
            playersLabel={t('views.team.players')}
          />
        </Box>

        <Box
          sx={{
            display: 'flex',
            justifyContent: 'center',
            flexWrap: 'wrap',
            alignItems: 'center',
            gap: { xs: 0.75, sm: 1.5 },
            mt: { xs: 1, sm: 1.25 },
            pt: 1,
            borderTop: '1px solid',
            borderColor: 'divider',
          }}
        >
          <MetaItem icon={<MapRounded sx={{ fontSize: '0.95rem' }} />}>{mapName}</MetaItem>
          <MetaItem icon={<GroupsRounded sx={{ fontSize: '0.95rem' }} />}>
            {gameMode}{attackers ? ` · ${t('views.team.attackers')}: ${attackers}` : ''}
          </MetaItem>
        </Box>
      </Box>
    </OverviewShell>
  )
}
