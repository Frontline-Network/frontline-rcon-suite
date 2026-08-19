import { useRef, useState } from "react";
import { styled } from "@mui/material/styles";
import {
  Card,
  CardHeader,
  CardContent,
  Avatar,
  List,
  ListItem,
  ListItemButton,
  ListItemAvatar,
  ListItemText,
  Typography,
  Box,
  Tabs,
  Tab,
} from "@mui/material";
import { usePlayerSidebar } from "@/hooks/usePlayerSidebar";
import GroupIcon from "@mui/icons-material/Group";
import { useTranslation } from "react-i18next";

// Styled components
const StyledCard = styled(Card)({
  margin: "0 auto",
  width: "100%",
  height: 250,
});

const ScrollableContent = styled(CardContent)({
  maxHeight: 175,
  overflow: "auto",
  padding: 0,
  "&:last-child": {
    paddingBottom: 0,
  },
  // Hide scrollbar for Chrome, Safari and Opera
  "&::-webkit-scrollbar": {
    display: "none",
  },
  // Hide scrollbar for IE, Edge and Firefox
  "msOverflowStyle": "none",
  scrollbarWidth: "none",
});

const StyledListItemButton = styled(ListItemButton)(({ theme }) => ({
  borderRadius: theme.shape.borderRadius,
  margin: theme.spacing(0.5, 0),
  padding: theme.spacing(0.5, 1),
  
  "&:not(.Mui-disabled)": {
    cursor: "pointer",
    "&:hover": {
      backgroundColor: theme.palette.action.hover,
    },
    transition: theme.transitions.create("background-color"),
  }
}));

const EmptyStateContainer = styled(Box)(({ theme }) => ({
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  padding: theme.spacing(1),
  height: "100%",
  color: theme.palette.text.secondary,
}));

const EmptyState = () => {
  const { t } = useTranslation();
  return (
    <EmptyStateContainer>
      <GroupIcon sx={{ fontSize: 48, mb: 2, opacity: 0.5 }} />
      <Typography variant="body1" gutterBottom>{t("dashboard.noUsersOnline")}</Typography>
      <Typography variant="body2" align="center">{t("dashboard.usersAppearOnline")}</Typography>
    </EmptyStateContainer>
  );
};

/**
 * @typedef {Object} User
 * @property {string} id - Unique identifier for the user
 * @property {string} name - Display name of the user
 * @property {string} [avatar] - Optional URL to user's avatar image
 */

/**
 * @typedef {Object} UserGroup
 * @property {string} group - Name of the user group
 * @property {ReactNode} label - Label of the user group
 * @property {User[]} users - Array of users in this group
 * @property {string} [manageLink] - Optional URL to manage the group
 */

/**
 * @param {UserGroup[]} onlineUsers - Array of user groups
 * @param {string} title - Title of the card
 * @returns {JSX.Element} - Rendered component
 */
const OnlineUsersCard = ({ onlineUsers, title }) => {
  const { t } = useTranslation();
  const { openWithId } = usePlayerSidebar();
  const [selectedTab, setSelectedTab] = useState(0);
  const scrollableContentRef = useRef();

  const handleTabChange = (event, newValue) => {
    setSelectedTab(newValue);
  };

  const handleUserClick = (userId) => {
    openWithId(userId);
  };

  return (
    <StyledCard>
      <CardHeader title={title} titleTypographyProps={{ variant: "h6" }}  />
      {onlineUsers.reduce((acc, group) => acc + group.users.length, 0) > 0 ? (
        <>
          <Tabs
            value={selectedTab}
            onChange={handleTabChange}
            variant="scrollable"
            scrollButtons="auto"
            aria-label={t("dashboard.userGroups")}
          >
            {onlineUsers.map((group, index) => (
              <Tab
                key={group.group}
                label={group.label}
              />
            ))}
          </Tabs>
          <ScrollableContent ref={scrollableContentRef}>
            {onlineUsers[selectedTab]?.users.length === 0 ? (
              <EmptyState />
            ) : (
              <List disablePadding sx={{ p: 0 }}>
                {onlineUsers[selectedTab]?.users.map((user, index) => (
                  <ListItem key={`${user.id || user.name}-${index}`} disablePadding>
                    <StyledListItemButton
                      onClick={() => handleUserClick(user.id)}
                      disabled={!user.id}
                    >
                      <ListItemAvatar>
                        <Avatar
                          src={user.avatar || undefined}
                          alt=""
                          sx={{ width: 24, height: 24 }}
                        >
                          {user.name
                            .split(" ")
                            .map((n) => n[0])
                            .join("")
                            .toUpperCase()}
                        </Avatar>
                      </ListItemAvatar>
                      <ListItemText
                        primary={user.name}
                        primaryTypographyProps={{
                          variant: "body2",
                          fontWeight: "medium",
                        }}
                      />
                    </StyledListItemButton>
                  </ListItem>
                ))}
              </List>
            )}
          </ScrollableContent>
        </>
      ) : (
        <EmptyState />
      )}
    </StyledCard>
  );
};

export default OnlineUsersCard;
