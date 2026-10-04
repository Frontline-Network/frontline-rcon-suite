import { lazy, Suspense } from "react";
import { useTheme } from "@mui/material/styles";
const CommandNavigationShell = lazy(() => import("./navigation/CommandNavigationShell"));
const WardogsNavigation = lazy(() => import("./navigation/WardogsNavigation"));

export default function SideMenu() {
  const theme = useTheme();
  return (
    <Suspense fallback={null}>
      {theme.frontline?.appearance?.preset === "wardogs" ? (
        <WardogsNavigation />
      ) : (
        <CommandNavigationShell />
      )}
    </Suspense>
  );
}
