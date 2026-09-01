import { LinearProgress } from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLoaderData, useRouteLoaderData } from "react-router-dom";
import { toast } from "react-toastify";
import { useTranslation } from "react-i18next";
import MapListBuilder from "../../MapListBuilder";
import { MapBuilderListItem } from "../../MapListItem";
import { SortableRotationList } from "../builder/SortableRotationList";
import {
  mapsManagerMutationOptions,
  mapsManagerQueryKeys,
} from "../../queries";
import { cmd } from "@/utils/fetchUtils";

function MapSequenceBuilder() {
  const { t } = useTranslation();
  const { maps } = useRouteLoaderData("maps");
  const { sequence: initialSequence } = useLoaderData();
  const queryClient = useQueryClient();
  const { data: sequence, isLoading } = useQuery({
    queryKey: mapsManagerQueryKeys.mapSequence,
    queryFn: cmd.GET_MAP_SEQUENCE,
    initialData: initialSequence,
    refetchOnMount: false,
  });
  const { mutate: saveSequence, isPending } = useMutation({
    ...mapsManagerMutationOptions.setMapSequence,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: mapsManagerQueryKeys.mapSequence,
      });
      queryClient.invalidateQueries({
        queryKey: mapsManagerQueryKeys.mapRotation,
      });
      toast.success(t("maps.sequenceSaved"));
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
    <>
      {isLoading && <LinearProgress />}
      <MapListBuilder
        maps={maps}
        selectedMaps={sequence.maps}
        slots={{
          SelectedMapList: SortableRotationList,
          MapListItem: MapBuilderListItem,
        }}
        onSave={saveSequence}
        isSaving={isPending}
        isSaveDisabled={isPending}
        selectedMapListProps={{
          title: t("maps.sequence"),
          description: t("maps.rotationWorkbench.sequenceDraftDescription"),
          saveLabel: t("maps.rotationWorkbench.publishSequence"),
          emptyTitle: t("maps.noMapsInSequence"),
          emptyDescription: t("maps.addMapsToSequence"),
          removeTooltip: t("maps.removeFromSequence"),
          showNext: false,
        }}
      />
    </>
  );
}

export default MapSequenceBuilder;
