import { IconButton, LinearProgress, Tooltip } from "@mui/material";
import {
  mapsManagerMutationOptions,
  mapsManagerQueryKeys,
  mapsManagerQueryOptions,
} from "../../queries";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLoaderData, useRouteLoaderData } from "react-router-dom";
import { toast } from "react-toastify";
import { useEffect, useMemo } from "react";
import { MapWhitelistList } from "../../MapList";
import { MapBuilderListItem } from "../../MapListItem";
import MapListBuilder from "../../MapListBuilder";
import RestoreIcon from "@mui/icons-material/Restore";
import { useTranslation } from "react-i18next";

function VotemapBuilderPage() {
  const { t } = useTranslation();
  const { maps } = useRouteLoaderData("maps");
  const loaderData = useLoaderData();
  const queryClient = useQueryClient();

  // Query to get current map rotation
  const { data: whitelist, isLoading: isLoadingWhitelist } = useQuery({
    ...mapsManagerQueryOptions.votemapWhitelist(),
    initialData: loaderData.whitelist,
    staleTime: 5_000,
    refetchOnMount: false,
  });

  const { mutate: saveWhitelist, isPending: isWhitelistSaving } = useMutation({
    ...mapsManagerMutationOptions.setWhitelist,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: mapsManagerQueryKeys.votemapWhitelist,
      });
      toast.success(t("maps.votemapWhitelistSaved"));
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

  const { mutate: resetWhitelist, isPending: isResetWhitelist } = useMutation({
    ...mapsManagerMutationOptions.resetVotemapWhitelist,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: mapsManagerQueryKeys.votemapWhitelist,
      });
      toast.success(t("maps.votemapWhitelistReset"));
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

  const whitelistMaps = useMemo(
    () => (whitelist ?? []).map((mapId) => maps.find((map) => map.id === mapId)).filter(Boolean),
    [whitelist, maps]
  );

  const handleWhitelistSave = (mapIds) => {
    saveWhitelist(mapIds);
  };

  const checkForOutdatedMapIds = () => {
    if (whitelist) {
      const mapLayers = [];
      const invalidMapIds = [];
      whitelist.forEach((mapId) => {
        const mapLayer = maps.find((mapLayer) => mapLayer.id === mapId);
        if (mapLayer) {
          mapLayers.push(mapLayer);
        } else {
          invalidMapIds.push(mapId);
        }
      });
      if (invalidMapIds.length) {
        toast.error(
          t("maps.votemapWhitelistOutdated", {
            maps: invalidMapIds.join(", "),
          })
        );
      }
    }
  };

  useEffect(checkForOutdatedMapIds, [whitelist, maps, t]);

  return (
    <>
      {isLoadingWhitelist && (
        <LinearProgress
          sx={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: { xs: "3px", lg: "2px" },
          }}
        />
      )}
      <MapListBuilder
        maps={maps}
        selectedMaps={whitelistMaps}
        onSave={handleWhitelistSave}
        isSaving={isWhitelistSaving}
        isSaveDisabled={isWhitelistSaving}
        exclusive={true}
        slots={{
          SelectedMapList: MapWhitelistList,
          MapListItem: MapBuilderListItem,
        }}
        actions={
          <Tooltip title={t("maps.resetVotemapWhitelist")}>
            <IconButton onClick={resetWhitelist} size="small" color="warning" disabled={isResetWhitelist}>
              <RestoreIcon />
            </IconButton>
          </Tooltip>
        }
      />
    </>
  );
}

export default VotemapBuilderPage;
