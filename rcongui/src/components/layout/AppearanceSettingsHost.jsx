import { lazy, Suspense, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/hooks/useAuth";
import { useAppStore } from "@/stores/app-state";
import { cmd } from "@/utils/fetchUtils";

const AppearanceSettingsDialog = lazy(() =>
  import("./AppearanceSettingsDialog")
);

// Keep account synchronization and the preview dialog above the replaceable
// navigation shell so changing themes cannot discard an unsaved draft.
export default function AppearanceSettingsHost() {
  const { permissions } = useAuth();
  const userKey = permissions?.user_name;
  const selectUser = useAppStore((state) => state.selectAppearanceUser);
  const hydrate = useAppStore((state) => state.hydrateAppearance);
  const open = useAppStore((state) => state.appearanceDialogOpen);
  const setOpen = useAppStore((state) => state.setAppearanceDialogOpen);
  const query = useQuery({
    queryKey: ["user", "appearance", userKey],
    queryFn: cmd.GET_OWN_APPEARANCE,
    enabled: Boolean(userKey),
    refetchOnWindowFocus: false,
    retry: 1,
  });
  useEffect(() => {
    if (userKey) selectUser(userKey);
  }, [selectUser, userKey]);
  useEffect(() => {
    if (userKey && query.data) hydrate(query.data, userKey);
  }, [query.data, hydrate, userKey]);
  return open ? (
    <Suspense fallback={null}>
      <AppearanceSettingsDialog open onClose={() => setOpen(false)} />
    </Suspense>
  ) : null;
}
