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

  return (
    <>
      <NavigationProgress />
      <Box sx={{ display: "flex" }}>
        <SideMenu />
        <AppNavbar />
        {/* Main content */}
        <Box
          component="main"
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
              mt: { xs: 13, lg: 0 },
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
    </>
  );
}
