import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  mapsManagerMutationOptions,
  mapsManagerQueryKeys,
  mapsManagerQueryOptions,
} from "../../queries";
import Padlock from "@/components/shared/Padlock";
import { Typography } from "@mui/material";
import { toast } from "react-toastify";
import { useLoaderData } from "react-router-dom";
import { useTranslation } from "react-i18next";

function MapRotationSettings() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const loaderData = useLoaderData()
  
  const { data: shuffleEnabled } = useQuery({
    ...mapsManagerQueryOptions.mapRotationShuffle(),
    initialData: loaderData.shuffleEnabled,
    refetchOnMount: false,
  });

  const { mutate: setShuffleEnabled } = useMutation({
    ...mapsManagerMutationOptions.setMapRotationShuffle,
    onSuccess: (response) => {
      const enabled = response.arguments.enabled
      queryClient.invalidateQueries({
        queryKey: mapsManagerQueryKeys.mapRotationShuffle,
      });
      toast.success(t("maps.rotationShuffleUpdated", { state: t(enabled ? "common.enabled" : "common.disabled") }));
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

  return (
    <Padlock
      label={
        <div
          style={{
            textAlign: "start",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <Typography variant={"body"}>{t("maps.rotationShuffle")}</Typography>
          <Typography variant={"caption"}>
            {t("maps.rotationShuffleDescription")}
          </Typography>
        </div>
      }
      name={"map-rotation-shuffle"}
      checked={shuffleEnabled}
      handleChange={setShuffleEnabled}
    />
  );
}

export default MapRotationSettings;
