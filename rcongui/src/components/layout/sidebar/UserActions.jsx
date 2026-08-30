import { useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import { Avatar, Box, Stack, Tooltip, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useAppStore } from "@/stores/app-state";
import { cmd } from "@/utils/fetchUtils";
import OptionsMenu from "../OptionsMenu";

export const UserActions = ({ compact = false }) => {
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
      direction={compact ? "column" : "row"}
      data-testid={compact ? "command-rail-user-actions" : undefined}
      sx={{
        width: compact ? 64 : "auto",
        p: compact ? 0.5 : 2,
        gap: compact ? 0.25 : 1,
        alignItems: "center",
        borderTop: "1px solid",
        borderColor: "divider",
      }}
    >
      <Tooltip
        title={permissions?.user_name ?? "?????"}
        placement={compact ? "right" : "top"}
      >
        <Avatar
          sizes="small"
          alt={permissions?.user_name?.toUpperCase() ?? "?"}
          sx={{ width: compact ? 34 : 36, height: compact ? 34 : 36 }}
        />
      </Tooltip>
      {!compact && (
        <Box sx={{ mr: "auto" }}>
          <Typography
            variant="body2"
            sx={{ fontWeight: 500, lineHeight: "16px" }}
          >
            {permissions?.user_name ?? "?????"}
          </Typography>
        </Box>
      )}
      <OptionsMenu />
    </Stack>
  );
};
