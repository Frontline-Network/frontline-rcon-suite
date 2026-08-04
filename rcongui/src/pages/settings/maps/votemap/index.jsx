import { Box, Tabs } from "@mui/material";
import { Outlet, useLocation } from "react-router-dom";
import { NavLinkTab } from "@/components/shared/NavLinkTab";
import { useTranslation } from "react-i18next";

/**
 * Map Rotation page that contains the map rotation builder component
 */
function VotemapPage() {
  const { t } = useTranslation();
  // Get active tab
  const location = useLocation();
  const tabs = [
    { label: t("maps.status"), href: "/settings/maps/votemap" },
    { label: t("maps.whitelist"), href: "/settings/maps/votemap/whitelist" },
    { label: t("maps.settings"), href: "/settings/maps/votemap/settings" },
  ];
  const activeTab = tabs.findIndex(({ href }) =>
    location.pathname.endsWith(href)
  );

  return (
    <>
      <Tabs value={activeTab}>
        {tabs.map(({ href, label }) => (
          <NavLinkTab key={href} label={label} to={href} />
        ))}
      </Tabs>
      {/* Move to Outlet */}
      <Box sx={{ mt: 1 }}>
        <Outlet />
      </Box>
    </>
  );
}

export default VotemapPage;
