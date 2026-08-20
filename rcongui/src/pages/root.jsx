import * as React from "react";
import { Container, Box, Stack } from "@mui/material";
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
  const { t } = useTranslation();

  return (
    <SystemUsageProvider>
      <TitleManager />
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
      <Box sx={{ display: "flex" }}>
        <SideMenu />
        <AppNavbar />
        {/* Main content */}
        <Box
          component="main"
          id="main-content"
          tabIndex={-1}
          sx={(theme) => ({
            flexGrow: 1,
            backgroundColor: theme.palette.background.default,
            overflow: "auto",
            height: "100vh",
          })}
        >
          <Stack
            sx={{
              alignItems: "center",
              mx: 0,
              pb: 4,
              // The compact navbar has two rows (navigation + live server state).
              // Keep the first page heading below the fixed bar at every mobile width.
              mt: { xs: 16, lg: 0 },
              minHeight: "100%",
            }}
          >
            <Header />
            <Container 
              maxWidth={widthMode}
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
                  <Outlet />
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
