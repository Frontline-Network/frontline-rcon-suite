import React from "react";
import { Box } from "@mui/material";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import PageHeader from "@/components/shared/PageHeader";
import { ControlPageLayout } from "../general-group/ControlPageLayout";

const sectionDefinitions = [
  {
    key: "/settings/services",
    labelKey: "navigation.links.services",
  },
  {
    key: "/settings/others/game-server",
    labelKey: "navigation.links.gameServer",
  },
  {
    key: "/settings/others/crcon",
    labelKey: "navigation.links.crcon",
  },
  {
    key: "/settings/others/steam",
    labelKey: "navigation.links.steam",
  },
  {
    key: "/settings/others/log-stream",
    labelKey: "navigation.links.logStream",
  },
  {
    key: "/settings/others/watch-kill-rate",
    labelKey: "navigation.links.watchKillRate",
  },
];

export default function SystemDiagnosticsLayout({ children }) {
  const { t, i18n } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const sections = sectionDefinitions.map((section) => ({
    ...section,
    label: t(section.labelKey),
  }));
  const activeSection =
    sections.find((section) => location.pathname.endsWith(section.key)) ||
    sections[0];
  const active = activeSection.key;
  const english = i18n.resolvedLanguage === "en";

  return (
    <>
      <PageHeader
        eyebrow={t("navigation.groups.systemDiagnostics")}
        title={activeSection.label}
        subtitle={
          english
            ? "Monitor services, connections and diagnostic data in one workspace."
            : "Dienste, Verbindungen und Diagnosedaten in einem Arbeitsbereich verwalten."
        }
      />
      <Box
        sx={{
          "& .MuiButton-root, & .MuiPaper-root, & .MuiOutlinedInput-root, & .MuiChip-root, & .MuiAlert-root":
            { borderRadius: 0 },
        }}
      >
        <ControlPageLayout
          sections={sections}
          active={active}
          onChange={(path) => navigate(path)}
          navigationWidth="250px"
        >
          {children}
        </ControlPageLayout>
      </Box>
    </>
  );
}
