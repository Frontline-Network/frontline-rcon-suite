import { cmd } from "@/utils/fetchUtils";
import { demoMapLayers, isFakeMode } from "@/mirage/demo-data";

export const loader = async ({ request }) => {
  const pathname = new URL(request.url).pathname.replace(/\/+$/, "");
  const votemapRouteWithoutCatalog =
    pathname === "/settings/maps/votemap" ||
    pathname.startsWith("/settings/maps/votemap/");

  if (votemapRouteWithoutCatalog) return { maps: [] };

  const maps = isFakeMode() ? demoMapLayers : await cmd.GET_MAPS();
  return { maps };
};
