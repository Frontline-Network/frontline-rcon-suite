import * as React from "react";
import { Container, Box, Stack, useTheme } from "@mui/material";
import AppNavbar from "@/components/layout/AppNavbar";
import Header from "@/components/layout/Header";
import SideMenu from "@/components/layout/SideMenu";
import { ToastContainer } from "react-toastify";
import { Outlet, redirect } from "react-router-dom";
import { cmd } from "@/utils/fetchUtils";
import "react-toastify/dist/ReactToastify.css";
import { ActionDialogProvider } from "@/hooks/useActionDialog";
import { PlayerSidebarProvider } from "@/hooks/usePlayerSidebar";
import { useAppStore } from "@/stores/app-state";
import NavigationProgress from "@/components/layout/NavigationProgress";
import { useTranslation } from "react-i18next";
import TitleManager from "@/features/title-manager/TitleManager";
import { SystemUsageProvider } from "@/features/system-usage/SystemUsageProvider";
import AppearanceSettingsHost from "@/components/layout/AppearanceSettingsHost";
import WardogsToolbar from "@/components/layout/wardogs/WardogsToolbar";
import WardogsPageFrame from "@/components/layout/wardogs/WardogsPageFrame";
import { themeBackground } from "@/themes/background";

export const loader = async () => {
  return null;
};

export const action = async ({ request }) => {
  const { intent } = Object.fromEntries(await request.formData());

  if (intent === "logout") {
    const success = await cmd.LOGOUT();

    if (success) {
      return redirect("/login");
    }
  }
};

export default function Root() {
  const widthMode = useAppStore((state) => state.widthMode);
  const isWardogs = useTheme().frontline?.appearance?.preset === "wardogs";
  const { t } = useTranslation();

  return (
    <SystemUsageProvider>
      <TitleManager />
      <AppearanceSettingsHost />
      <NavigationProgress />
      <Box
        component="a"
        href="#main-content"
        sx={(theme) => ({
          position: "fixed",
          top: 8,
          left: 8,
          zIndex: theme.zIndex.tooltip + 1,
          px: 2,
          py: 1,
          borderRadius: 1,
          bgcolor: "background.paper",
          color: "text.primary",
          border: "2px solid",
          borderColor: "primary.main",
          boxShadow: theme.shadows[8],
          transform: "translateY(-160%)",
          transition: theme.transitions.create("transform", {
            duration: theme.transitions.duration.shortest,
          }),
          "&:focus": {
            transform: "translateY(0)",
          },
        })}
      >
        {t("common.skipToContent")}
      </Box>
      <Box
        sx={{
          "--app-header-height": {
            xs: isWardogs ? "64px" : "108px",
            sm: isWardogs ? "64px" : "108px",
            md: "0px",
          },
          "--wardogs-gutter": "clamp(24px, 3.2vw, 72px)",
          "--mobile-bottom-nav-height": isWardogs ? "0px" : "64px",
          display: "flex",
          minHeight: "100dvh",
        }}
      >
        <SideMenu />
        {!isWardogs && <AppNavbar />}
        {/* Main content */}
        <Box
          component="main"
          id="main-content"
          tabIndex={-1}
          sx={(theme) => ({
            flexGrow: 1,
            backgroundColor: theme.palette.background.default,
            ...themeBackground(theme),
            overflow: "auto",
            height: "100dvh",
            scrollPaddingTop: "var(--app-header-height)",
          })}
        >
          <Stack
            sx={{
              alignItems: "center",
              mx: 0,
              pb: {
                xs: isWardogs
                  ? "env(safe-area-inset-bottom)"
                  : "calc(var(--mobile-bottom-nav-height) + env(safe-area-inset-bottom) + 16px)",
                md: 4,
              },
              // The compact navbar has two rows (navigation + live server state).
              // Keep the first page heading below the fixed bar at every mobile width.
              pt: {
                xs: "calc(var(--app-header-height) + env(safe-area-inset-top))",
                md: 0,
              },
              minHeight: "100%",
            }}
          >
            {isWardogs ? <WardogsToolbar /> : <Header />}
            <Container
              maxWidth={isWardogs ? false : widthMode}
              sx={{
                display: "flex",
                flexDirection: "column",
                flexGrow: 1,
                position: "relative",
                minHeight: "100%",
                px: { xs: 1.5, md: 2.5 },
                pt: { xs: 1, md: 1.25 },
                maxWidth: widthMode === false ? "none" : undefined,
              }}
            >
              <ActionDialogProvider>
                <PlayerSidebarProvider>
                  <WardogsPageFrame active={isWardogs}>
                    <Outlet />
                  </WardogsPageFrame>
                </PlayerSidebarProvider>
              </ActionDialogProvider>
            </Container>
          </Stack>
        </Box>
      </Box>
      <ToastContainer />
    </SystemUsageProvider>
  );
}
