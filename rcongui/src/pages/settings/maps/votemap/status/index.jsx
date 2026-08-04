import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  mapsManagerMutationOptions,
  mapsManagerQueryKeys,
  mapsManagerQueryOptions,
} from "../../queries";
import { MapList } from "../../MapList";
import { MapVotemapListItem } from "../../MapListItem";
import {
  Box,
  Button,
  CircularProgress,
  Divider,
  Stack,
  styled,
  Typography,
} from "@mui/material";
import PowerOffIcon from "@mui/icons-material/PowerOff";
import PowerIcon from "@mui/icons-material/Power";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import { useLoaderData } from "react-router-dom";
import { toast } from "react-toastify";
import { useTranslation } from "react-i18next";

const MapListContainer = styled(Box)(({ theme }) => ({
  width: "100%",
  [theme.breakpoints.up("md")]: {
    width: "50%",
  },
}));

const ActionsContainer = styled(Box)(({ theme }) => ({
  width: "100%",
  padding: theme.spacing(1),
  [theme.breakpoints.up("md")]: {
    width: "50%",
    borderLeft: `1px solid ${theme.palette.divider}`,
  },
}));

function VotemapStatusPage() {
  const { t } = useTranslation();
  const loaderData = useLoaderData();
  const queryClient = useQueryClient();

  const { data: mapListStatus } = useQuery({
    ...mapsManagerQueryOptions.votemapStatus(),
    initialData: loaderData.mapListStatus,
    refetchInterval: 15_000,
    staleTime: 5_000,
    refetchOnMount: false,
  });

  const { data: config } = useQuery({
    ...mapsManagerQueryOptions.voteMapConfig(),
    initialData: loaderData.config,
    refetchInterval: 15_000,
    staleTime: 5_000,
    refetchOnMount: false,
  });
  const normalizedMapListStatus = Array.isArray(mapListStatus)
    ? mapListStatus
    : [];
  const isVotemapEnabled = Boolean(config?.enabled);

  const { mutate: toggleVotemap, isPending: isToggling } = useMutation({
    ...mapsManagerMutationOptions.setVotemapConfig,
    onSuccess: (response) => {
      const enabled = response.arguments.enabled;
      queryClient.invalidateQueries([
        mapsManagerQueryKeys.voteMapConfig,
        mapsManagerQueryKeys.votemapStatus,
      ]);
      toast.success(t("maps.votemapUpdated", { state: enabled ? t("common.enabled") : t("common.disabled") }));
    },
    onError: (error) => {
      toast.error(
        <div>
          <span>{error.name}</span>
          <p>{error.message}</p>
        </div>
      );
    },
  });

  const { mutate: resetVotemap, isPending: isReseting } = useMutation({
    ...mapsManagerMutationOptions.resetVotemapState,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: mapsManagerQueryKeys.votemapStatus,
      });
      toast.success(t("maps.votemapReset"));
    },
    onError: (error) => {
      toast.error(
        <div>
          <span>{error.name}</span>
          <p>{error.message}</p>
        </div>
      );
    },
  });

  const handleVotemapToggle = () => {
    toggleVotemap({
      ...config,
      enabled: !isVotemapEnabled,
    });
  };

  return (
    <Stack direction={{ xs: "column-reverse", md: "row" }} spacing={1}>
      <MapListContainer>
        <MapList
          maps={normalizedMapListStatus.map((s) => s.map)}
          sort={false}
          renderItem={(mapLayer, index) => (
            <MapVotemapListItem
              key={mapLayer.id}
              mapLayer={mapLayer}
              voters={normalizedMapListStatus[index].voters}
            />
          )}
        />
      </MapListContainer>
      <ActionsContainer>
        <Typography variant="subtitle2" component={"div"}>
          {t("maps.status")}: {isVotemapEnabled ? `🟢 ${t("common.enabled")}` : `🔴 ${t("common.disabled")}`}
        </Typography>
        <Typography variant="subtitle2" component={"div"}>
          {t("maps.next")}:{" "}
          {isVotemapEnabled
            ? normalizedMapListStatus[0]?.map?.pretty_name ?? t("common.unknown")
            : "–"}
        </Typography>
        <Divider orientation="horizontal" sx={{ my: 1 }} />
        <Stack direction="row" spacing={1} alignItems={"center"}>
          <Button
            onClick={handleVotemapToggle}
            startIcon={
              isToggling ? (
                <CircularProgress size={20} />
              ) : isVotemapEnabled ? (
                <PowerOffIcon />
              ) : (
                <PowerIcon />
              )
            }
            variant="contained"
            disabled={isToggling}
            color={isVotemapEnabled ? "error" : "success"}
            sx={{ minWidth: 120 }}
            size="small"
          >
            {isVotemapEnabled ? t("maps.disableVotemap") : t("maps.enableVotemap")}
          </Button>
          <Typography variant="caption">
            {isVotemapEnabled
              ? t("maps.disableVotemapDescription")
              : t("maps.enableVotemapDescription")}
          </Typography>
        </Stack>
        <Divider flexItem orientation="horizontal" sx={{ my: 1 }} />
        <Stack direction="row" spacing={1} alignItems={"center"}>
          <Button
            onClick={resetVotemap}
            disabled={isReseting}
            startIcon={
              isReseting ? <CircularProgress size={20} /> : <AutorenewIcon />
            }
            variant="contained"
            color="warning"
            sx={{ minWidth: 120 }}
            size="small"
          >
            {t("maps.resetVotemap")}
          </Button>
          <Typography variant="caption">
            {t("maps.resetVotemapDescription")}
          </Typography>
        </Stack>
      </ActionsContainer>
    </Stack>
  );
}

export default VotemapStatusPage;
