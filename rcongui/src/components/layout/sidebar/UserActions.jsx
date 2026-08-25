import { useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import { Avatar, Box, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useAppStore } from "@/stores/app-state";
import { cmd } from "@/utils/fetchUtils";
import OptionsMenu from "../OptionsMenu";

export const UserActions = () => {
  const { permissions } = useAuth();
  const userKey = permissions?.user_name;
  const selectAppearanceUser = useAppStore(
    (state) => state.selectAppearanceUser
  );
  const hydrateAppearance = useAppStore((state) => state.hydrateAppearance);
  const appearanceQuery = useQuery({
    queryKey: ["user", "appearance", userKey],
    queryFn: cmd.GET_OWN_APPEARANCE,
    enabled: Boolean(userKey),
    refetchOnWindowFocus: false,
    retry: 1,
  });

  useEffect(() => {
    if (userKey) selectAppearanceUser(userKey);
  }, [selectAppearanceUser, userKey]);

  useEffect(() => {
    if (userKey && appearanceQuery.data) {
      hydrateAppearance(appearanceQuery.data, userKey);
    }
  }, [appearanceQuery.data, hydrateAppearance, userKey]);

  return (
    <Stack
      direction="row"
      sx={{
        p: 2,
        gap: 1,
        alignItems: "center",
        borderTop: "1px solid",
        borderColor: "divider",
      }}
    >
      <Avatar
        sizes="small"
        alt={permissions?.user_name?.toUpperCase() ?? "?"}
        sx={{ width: 36, height: 36 }}
      />
      <Box sx={{ mr: "auto" }}>
        <Typography
          variant="body2"
          sx={{ fontWeight: 500, lineHeight: "16px" }}
        >
          {permissions?.user_name ?? "?????"}
        </Typography>
      </Box>
      <OptionsMenu />
    </Stack>
  );
};
