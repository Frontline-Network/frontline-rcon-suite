import { Box, Stack, useMediaQuery } from "@mui/material";
import NavbarBreadcrumbs from "./NavbarBreadcrumbs";
import ToggleWidthMode from "./ToggleWidthMode";
import LanguageSelector from "./LanguageSelector";
import MenuButton from "./MenuButton";
import MenuRoundedIcon from "@mui/icons-material/MenuRounded";
import MenuOpenIcon from "@mui/icons-material/MenuOpen";
import { useAppStore } from "@/stores/app-state";
import ServerStatus from "../Header/server-status";
import { useTranslation } from "react-i18next";
import { useTheme } from "@mui/material/styles";

export default function Header() {
  const { t } = useTranslation();
  const isWardogs = useTheme().frontline?.appearance?.preset === "wardogs";
  const openDrawer = useAppStore((state) => isWardogs ? state.wardogsDrawerOpen : state.openDrawer);
  const toggleDrawer = useAppStore((state) => isWardogs ? state.toggleWardogsDrawer : state.toggleDrawer);
  const isDesktop = useMediaQuery((theme) => theme.breakpoints.up("md"));

  if (!isDesktop) return null;

  return (
    <Stack
      data-testid="desktop-header"
      direction="row"
      sx={{
        display: { xs: "none", md: "flex" },
        width: "100%",
        alignItems: { xs: "flex-start", md: "center" },
        justifyContent: "space-between",
        minHeight: 60,
        py: 1,
        px: { xs: 0, md: 2.5 },
        borderBottom: "1px solid",
        borderColor: "divider",
      }}
      spacing={2}
    >
      <Stack direction="row" sx={{ gap: 1, flex: 1, minWidth: 0 }}>
        <MenuButton
          aria-label={t("navigation.toggleMenu")}
          onClick={toggleDrawer}
          sx={{ display: { xs: "none", md: "inline-flex" } }}
        >
          {!openDrawer ? <MenuRoundedIcon /> : <MenuOpenIcon />}
        </MenuButton>
        <NavbarBreadcrumbs />
      </Stack>
      <ServerStatus />
      <Stack direction="row" sx={{ gap: 1, flexShrink: 0 }}>
        <Box sx={{ display: "flex", gap: 2, width: "fit-content" }}>
          <ToggleWidthMode />
          <LanguageSelector />
        </Box>
      </Stack>
    </Stack>
  );
}
