import { NavLinkTab } from "@/components/shared/NavLinkTab";
import { Alert, Box, Tabs } from "@mui/material";
import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

function SettingsPage() {
  const { t } = useTranslation();
  const [showAlert, setShowAlert] = useState(true);
  // Get active tab
  const location = useLocation();
  const tabs = [
    { label: t("settings.generalTabs.general"), href: "/settings/general" },
    { label: t("settings.generalTabs.game"), href: "/settings/game" },
    { label: t("settings.generalTabs.serverName"), href: "/settings/server-name" },
    { label: t("settings.generalTabs.adminCam"), href: "/settings/admin-cam-notifications" },
    { label: t("settings.generalTabs.crcon"), href: "/settings/crcon" },
  ];
  const activeTab = tabs.findIndex(({ href }) =>
    location.pathname.endsWith(href)
  );

  return (
    <>
      <Tabs
        value={activeTab}
        variant="scrollable"
        scrollButtons="auto"
        allowScrollButtonsMobile
      >
        {tabs.map(({ href, label }) => (
          <NavLinkTab key={href} label={label} to={href} />
        ))}
      </Tabs>
      <Box sx={{ mt: 1 }}>
        {showAlert && (
          <Alert
            severity="info"
            onClose={() => setShowAlert(false)}
            sx={{ mb: 4 }}
          >
            {t("settings.generalTabs.notice")}
          </Alert>
        )}
        <Outlet />
      </Box>
    </>
  );
}

export default SettingsPage;
