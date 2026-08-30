import { NavLinkTab } from "@/components/shared/NavLinkTab";
import { Alert, Box, Tabs } from "@mui/material";
import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import PageHeader from "@/components/shared/PageHeader";

function SettingsPage() {
  const { t, i18n } = useTranslation();
  const [showAlert, setShowAlert] = useState(true);
  // Get active tab
  const location = useLocation();
  const tabs = [
    { label: t("settings.generalTabs.general"), href: "/settings/general" },
    { label: t("settings.generalTabs.game"), href: "/settings/game" },
    {
      label: t("settings.generalTabs.serverName"),
      href: "/settings/server-name",
    },
    {
      label: t("settings.generalTabs.adminCam"),
      href: "/settings/admin-cam-notifications",
    },
    { label: t("settings.generalTabs.crcon"), href: "/settings/crcon" },
  ];
  const activeTab = tabs.findIndex(({ href }) =>
    location.pathname.endsWith(href)
  );
  const pageHeaders = [
    {
      de: [
        "Allgemeine Serversteuerung",
        "Spielablauf, Zugang und Moderation zentral verwalten.",
      ],
      en: [
        "General server control",
        "Manage gameplay, access and moderation from one clear workspace.",
      ],
    },
    {
      de: [
        "Spiel- und Rundensteuerung",
        "Wetter, Runden- und Aufwärmzeiten übersichtlich konfigurieren.",
      ],
      en: [
        "Game and round control",
        "Configure weather, round and warm-up times clearly.",
      ],
    },
    {
      de: [
        "Servername verwalten",
        "Öffentlichen Namen und technische Verbindung getrennt pflegen.",
      ],
      en: [
        "Manage server name",
        "Maintain the public name and technical connection separately.",
      ],
    },
    {
      de: [
        "Admin-Kamera",
        "Benachrichtigungen beim Betreten der Admin-Kamera festlegen.",
      ],
      en: [
        "Admin camera",
        "Configure notifications when administrators enter the camera.",
      ],
    },
    {
      de: [
        "CRCON-App & Werkzeuge",
        "Frontline-Geräte koppeln und die CRCON-Verbindung verwalten.",
      ],
      en: [
        "CRCON app and utilities",
        "Pair Frontline devices and manage the CRCON connection.",
      ],
    },
  ];
  const language = i18n.resolvedLanguage === "en" ? "en" : "de";
  const [pageTitle, pageSubtitle] = pageHeaders[activeTab]?.[language] || [
    tabs[activeTab]?.label,
    "",
  ];

  return (
    <>
      {activeTab >= 0 && (
        <PageHeader
          eyebrow={
            language === "en" ? "Server configuration" : "Serverkonfiguration"
          }
          title={pageTitle}
          subtitle={pageSubtitle}
        />
      )}
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
        {showAlert && activeTab !== 0 && (
          <Alert
            severity="info"
            onClose={() => setShowAlert(false)}
            sx={{ mb: 1.5, borderRadius: 0, py: 0.25 }}
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
