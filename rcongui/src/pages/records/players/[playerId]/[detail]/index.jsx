import { useState } from 'react';
import {
  Typography,
  TextField,
  MenuItem,
  CardContent,
  Button,
  Box,
  InputAdornment,
  Divider,
  Stack,
} from '@mui/material';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { useParams, useOutletContext, Form, useSearchParams, useSubmit, useRevalidator } from 'react-router-dom';
import {
  DetailCard,
  ScrollableContent,
  ListItem,
  FilterSection,
} from '../styled';
import dayjs from 'dayjs';
import PlayerLogs from './logs';
import ProfileDetails from './profile-details';
import { useTranslation } from "react-i18next";

export default function PlayerDetailView() {
  const { t } = useTranslation();
  const { detail } = useParams();
  const { profile, submit } = useOutletContext();
  const [searchParams, setSearchParams] = useSearchParams();
  const revalidator = useRevalidator();
  const [newComment, setNewComment] = useState('');
  const [filters, setFilters] = useState({
    sessions: { 
      search: '', 
      startDate: null, 
      endDate: null 
    },
    actions: { search: '', type: '' },
    names: { search: '' },
    comments: { 
      search: '', 
      author: '', 
      startDate: null, 
      endDate: null 
    },
  });

  const formatDate = (dateString) => {
    return dayjs(dateString).format('lll');
  };

  const handleFilterChange = (tab, key, value) => {
    setFilters((prev) => ({ ...prev, [tab]: { ...prev[tab], [key]: value } }));
  };

  const handleSessionCountChange = (event) => {
    const value = event.target.value;
    if (value && value > 0) {
      setSearchParams(prev => {
        prev.set('num_sessions', value);
        return prev;
      });
    }
  };

  const handleCommentSubmit = async (event) => {
    event.preventDefault();
    const formData = new FormData();
    formData.append('player_id', profile.player_id);
    formData.append('comment', newComment);
    
    const result = await submit(formData, { 
      method: 'post',
      replace: true,
    });

    if (result?.ok) {
      setNewComment('');
      revalidator.revalidate();
    }
  };

  const filterData = (data, tab) => {
    return data.filter((item) => {
      const searchLower = filters[tab].search.toLowerCase();
      switch (tab) {
        case 'sessions':
          const startDate = filters.sessions.startDate ? dayjs(filters.sessions.startDate) : null;
          const endDate = filters.sessions.endDate ? dayjs(filters.sessions.endDate) : null;
          const sessionStart = dayjs(item.start);
          const sessionEnd = item.end ? dayjs(item.end) : null;

          return (
            (!startDate || sessionStart.isAfter(startDate)) &&
            (!endDate || (sessionEnd && sessionEnd.isBefore(endDate))) &&
            (sessionStart.format('lll').toLowerCase().includes(searchLower) || 
             (sessionEnd && sessionEnd.format('lll').toLowerCase().includes(searchLower)))
          );
        case 'received-actions':
          return (
            item.action_type.includes(filters.actions.type) &&
            (item.reason.toLowerCase().includes(searchLower) || item.by.toLowerCase().includes(searchLower))
          );
        case 'names':
          return item.name.toLowerCase().includes(searchLower);
        case 'comments':
          const commentStartDate = filters.comments.startDate ? dayjs(filters.comments.startDate) : null;
          const commentEndDate = filters.comments.endDate ? dayjs(filters.comments.endDate) : null;
          const commentDate = dayjs(item.creation_time);

          return (
            item.content.toLowerCase().includes(searchLower) &&
            item.by.includes(filters.comments.author) &&
            (!commentStartDate || commentDate.isAfter(commentStartDate)) &&
            (!commentEndDate || commentDate.isBefore(commentEndDate))
          );
        default:
          return true;
      }
    });
  };

  const renderContent = () => {
    switch (detail) {
      case 'sessions':
        return (
          <div>
            <FilterSection>
              <TextField
                sx={{ maxWidth: '200px' }}
                label={t("records.playerDetails.sessionCount")}
                type="number"
                value={searchParams.get('num_sessions') || '10'}
                onChange={handleSessionCountChange}
                size="small"
                InputProps={{
                  endAdornment: <InputAdornment position="end">{t("records.playerDetails.sessions")}</InputAdornment>,
                }}
                inputProps={{
                  min: 1,
                  max: 1000,
                }}
              />
              <Box className="date-inputs">
                <DateTimePicker
                  label={t("records.playerDetails.startDate")}
                  value={filters.sessions.startDate}
                  format='lll'
                  onChange={(newValue) => handleFilterChange('sessions', 'startDate', newValue)}
                  slotProps={{ textField: { size: 'small' } }}
                />
                <DateTimePicker
                  label={t("records.playerDetails.endDate")}
                  value={filters.sessions.endDate}
                  format='lll'
                  onChange={(newValue) => handleFilterChange('sessions', 'endDate', newValue)}
                  slotProps={{ textField: { size: 'small' } }}
                />
              </Box>
            </FilterSection>
            <Stack direction="row" justifyContent="space-between" sx={{ p: 2 }}>
              <Typography variant="body2">{t("records.playerDetails.totalSessions")}: {filterData(profile.sessions, 'sessions').length}</Typography>
              <Typography variant="body2">
                {t("records.playerDetails.totalPlaytime")}: {filterData(profile.sessions, 'sessions').reduce((acc, session) =>
                  acc + (session.end === null ? 0 : dayjs(session.end).diff(dayjs(session.start), 'minutes')), 0)
                } {t("records.playerDetails.minutes")}
              </Typography>
            </Stack>
            <Divider />
            <ScrollableContent>
              {filterData(profile.sessions, 'sessions').map((session, index) => (
                <ListItem sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', justifyContent: 'space-between' }} key={index}>
                  <Typography variant="body2">{t("records.playerDetails.start")}: {formatDate(session.start)}</Typography>
                  <Typography variant="body2">
                    {t("records.playerDetails.duration")}: {session.end === null ? t("common.unknown") : `${dayjs(session.end).diff(dayjs(session.start), "minutes")} ${t("records.playerDetails.minutes")}`}
                  </Typography>
                  <Typography variant="body2">{t("records.playerDetails.end")}: {session.end === null ? t("common.unknown") : formatDate(session.end)}</Typography>
                </ListItem>
              ))}
            </ScrollableContent>
          </div>
        );

      case 'actions':
        return (
          <div>
            <FilterSection>
              <TextField
                label={t("records.playerDetails.searchActions")}
                value={filters.actions.search}
                onChange={(e) => handleFilterChange('actions', 'search', e.target.value)}
                size="small"
              />
              <TextField
                select
                label={t("records.playerDetails.actionType")}
                value={filters.actions.type}
                onChange={(e) => handleFilterChange('actions', 'type', e.target.value)}
                size="small"
              >
                <MenuItem value="">{t("common.all")}</MenuItem>
                <MenuItem value="TEMPBAN">{t("actions.types.TEMPBAN")}</MenuItem>
                <MenuItem value="PERMABAN">{t("actions.types.PERMABAN")}</MenuItem>
                <MenuItem value="PUNISH">{t("actions.types.PUNISH")}</MenuItem>
                <MenuItem value="KICK">{t("actions.types.KICK")}</MenuItem>
                <MenuItem value="MESSAGE">{t("actions.types.MESSAGE")}</MenuItem>
              </TextField>
            </FilterSection>
            <ScrollableContent>
              {filterData(profile.received_actions, 'actions').map((action, index) => (
                <ListItem key={index}>
                  <Typography variant="subtitle1">
                    {t(`actions.types.${action.action_type}`, { defaultValue: action.action_type })}
                  </Typography>
                  <Typography>{t("records.playerDetails.reason")}: {action.reason}</Typography>
                  <Typography>{t("records.playerDetails.by")}: {action.by}</Typography>
                  <Typography>{t("records.playerDetails.time")}: {formatDate(action.time)}</Typography>
                </ListItem>
              ))}
            </ScrollableContent>
          </div>
        );

      case 'names':
        return (
          <div>
            <FilterSection>
              <TextField
                label={t("records.playerDetails.searchNames")}
                value={filters.names.search}
                onChange={(e) => handleFilterChange('names', 'search', e.target.value)}
                size="small"
                fullWidth
              />
            </FilterSection>
            <ScrollableContent>
              {filterData(profile.names, 'names').map((name, index) => (
                <ListItem key={index}>
                  <Typography variant="subtitle1">{name.name}</Typography>
                  <Typography>{t("records.playerDetails.lastSeen")}: {formatDate(name.last_seen)}</Typography>
                </ListItem>
              ))}
            </ScrollableContent>
          </div>
        );

      case 'comments':
        return (
          <div>
            <Form onSubmit={handleCommentSubmit}>
              <FilterSection>
                <TextField
                  label={t("records.playerDetails.newComment")}
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  size="small"
                  fullWidth
                  multiline
                  rows={2}
                />
                <Button type="submit" variant="contained" disabled={!newComment.trim()}>
                  {t("records.playerDetails.addComment")}
                </Button>
              </FilterSection>
            </Form>
            <FilterSection>
              <TextField
                label={t("records.playerDetails.searchComments")}
                value={filters.comments.search}
                onChange={(e) => handleFilterChange('comments', 'search', e.target.value)}
                size="small"
              />
              <TextField
                label={t("records.playerDetails.author")}
                value={filters.comments.author}
                onChange={(e) => handleFilterChange('comments', 'author', e.target.value)}
                size="small"
              />
              <Box className="date-inputs">
                <DateTimePicker
                  label={t("records.playerDetails.startDate")}
                  value={filters.comments.startDate}
                  onChange={(newValue) => handleFilterChange('comments', 'startDate', newValue)}
                  slotProps={{ textField: { size: 'small' } }}
                />
                <DateTimePicker
                  label={t("records.playerDetails.endDate")}
                  value={filters.comments.endDate}
                  onChange={(newValue) => handleFilterChange('comments', 'endDate', newValue)}
                  slotProps={{ textField: { size: 'small' } }}
                />
              </Box>
            </FilterSection>
            <ScrollableContent>
              {filterData(profile.comments, 'comments').map((comment, index) => (
                <ListItem key={index}>
                  <Typography>{comment.content}</Typography>
                  <Typography>{t("records.playerDetails.by")}: {comment.by}</Typography>
                  <Typography>{t("records.playerDetails.time")}: {formatDate(comment.creation_time)}</Typography>
                </ListItem>
              ))}
            </ScrollableContent>
          </div>
        );

      case 'logs':
        return <PlayerLogs />;

      default:
        return <ProfileDetails />;
    }
  };

  return (
    <DetailCard elevation={0} variant="outlined">
      <CardContent>
        {renderContent()}
      </CardContent>
    </DetailCard>
  );
}
