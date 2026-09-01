export const getMobileNavigationValue = (pathname) => {
  if (pathname.startsWith("/incidents")) return "incidents";
  if (pathname.startsWith("/records/players")) return "players";
  if (pathname.startsWith("/views/live")) return "operations";
  if (pathname === "/" || pathname.startsWith("/mobile/operations")) {
    return "server-operations";
  }
  if (
    pathname.startsWith("/views/team") ||
    pathname.startsWith("/views/autobalancer") ||
    pathname.startsWith("/settings/maps") ||
    pathname.startsWith("/settings/autosettings")
  ) {
    return "server-operations";
  }
  return "more";
};
