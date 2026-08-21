import { Box, Tabs } from "@mui/material";
import { Outlet, useLocation } from "react-router-dom";
import { NavLinkTab } from "@/components/shared/NavLinkTab";
import { useTranslation } from "react-i18next";

/**
 * Map Rotation page that contains the map rotation builder component
 */
function MapRotation() {
  const { t } = useTranslation();
  // Get active tab
  const location = useLocation();
  const tabs = [
    { label: t("maps.builder"), href: "/settings/maps/rotation" },
    { label: t("maps.sequence"), href: "/settings/maps/rotation/sequence" },
    { label: t("maps.settings"), href: "/settings/maps/rotation/settings" },
  ];
  const activeTab = tabs.findIndex(({ href }) =>
    location.pathname.endsWith(href)
  );

  return (
    <>
      <Tabs value={activeTab}>
        <NavLinkTab label={t("maps.builder")} to={""} />
        <NavLinkTab label={t("maps.sequence")} to={"sequence"} />
        <NavLinkTab label={t("maps.settings")} to={"settings"} />
      </Tabs>
      {/* Move to Outlet */}
      <Box sx={{ mt: 1 }}>
        <Outlet />
      </Box>
    </>
  );
}

export default MapRotation;
