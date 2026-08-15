import { Box, Stack } from "@mui/material";
import NavbarBreadcrumbs from "./NavbarBreadcrumbs";
import ToggleWidthMode from "./ToggleWidthMode";
import LanguageSelector from "./LanguageSelector";
import MenuButton from "./MenuButton";
import MenuRoundedIcon from "@mui/icons-material/MenuRounded";
import MenuOpenIcon from "@mui/icons-material/MenuOpen";
import { useAppStore } from "@/stores/app-state";
import ServerStatus from "../Header/server-status";

export default function Header() {
  const openDrawer = useAppStore((state) => state.openDrawer);
  const toggleDrawer = useAppStore((state) => state.toggleDrawer);

  return (
    <Stack
      direction="row"
      sx={{
        display: { xs: "none", lg: "flex" },
        width: "100%",
        alignItems: { xs: "flex-start", lg: "center" },
        justifyContent: "space-between",
        minHeight: 60,
        py: 1,
        px: { xs: 0, lg: 2.5 },
        borderBottom: "1px solid",
        borderColor: "divider",
      }}
      spacing={2}
    >
      <Stack direction="row" sx={{ gap: 1, flex: 1, minWidth: 0 }}>
        <MenuButton
          aria-label="toggle-menu"
          onClick={toggleDrawer}
          sx={{ display: { xs: "none", lg: "inline-flex" } }}
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
