import { useTheme } from "@mui/material/styles";
import CommandNavigationShell from "./navigation/CommandNavigationShell";
import WardogsNavigation from "./navigation/WardogsNavigation";

export default function SideMenu() {
  const theme = useTheme();
  return theme.frontline?.appearance?.preset === "wardogs" ? (
    <WardogsNavigation />
  ) : (
    <CommandNavigationShell />
  );
}
