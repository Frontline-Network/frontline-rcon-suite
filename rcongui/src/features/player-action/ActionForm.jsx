import { Box, Button, Stack } from "@mui/material";
import { useForm } from "react-hook-form";
import { BadgeList } from "./BadgeList";
import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import PlayerSearchField from "@/components/form/custom/PlayerSearchField";
import { executeQueued } from "./executionQueue.mjs";

const ACTION_STATUS = {
  default: "default",
  pending: "warning",
  error: "error",
  success: "success",
};

const initRecipients = (recipients) =>
  recipients.map((recipient) => {
    if ("profile" in recipient) {
      recipient.name = recipient?.name ?? recipient?.profile.names[0]?.name;
    } else {
      recipient.name = recipient?.name ?? recipient?.names[0]?.name;
    }
    const label = recipient.name;
    return {
      recipient: recipient,
      status: recipient?.status ?? ACTION_STATUS.default,
      label,
    };
  });

export const ActionForm = ({
  state: actionState,
  actionHandlers,
  locked = false,
  onRecipientCountChange,
}) => {
  const { t } = useTranslation();
  const {
    handleSubmit,
    formState: { errors },
    ...formProps
  } = useForm({
    // to make the text inputs detect any change when calling
    // setValue from the react-hook-form
    defaultValues: {
      message: "",
      reason: "",
    },
  });
  const { recipients, action, params } = actionState;
  const { submitRef, setLoading, setError, setSuccess } = actionHandlers;
  const [recipientStates, setRecipientStates] = useState(
    initRecipients(recipients)
  );
  const queryClient = useQueryClient();

  useEffect(() => {
    setRecipientStates(initRecipients(recipients));
  }, [recipients]);

  useEffect(() => {
    onRecipientCountChange?.(recipientStates.length);
  }, [onRecipientCountChange, recipientStates.length]);

  const onSubmit = useCallback(
    async (data) => {
      const getPlayerId = (recipient) =>
        recipient.player_id ?? recipient?.profile?.player_id;
      let allSuccess = true;
      setError(null);
      setSuccess(false);
      setLoading(true);
      // get list of all selected players and ids
      const steamIds = recipientStates.map(({ recipient }) =>
        getPlayerId(recipient)
      );
      const players = recipientStates.map(({ recipient }) => recipient.name);
      // map each to a request payload
      const payloads = [];
      for (let i = 0; i < players.length; i++) {
        payloads.push({
          player_name: players[i],
          player_id: steamIds[i],
          ...data,
          ...params,
        });
      }
      // Validate a reviewed group once, before any member is switched. The
      // final confirmation may be much later than opening the action dialog.
      try {
        await action.preflight?.(payloads);
      } catch (error) {
        setError(error);
        setLoading(false);
        return;
      }
      // Update UI to signalize pending state
      setRecipientStates((prevState) =>
        prevState.map((state) => ({
          ...state,
          status: ACTION_STATUS.pending,
        }))
      );
      // Large message selections must not hit the game server all at once.
      // Actions without queue settings keep their existing parallel behavior.
      const responses = action.execution
        ? await executeQueued(payloads, action.execute, action.execution)
        : await Promise.allSettled(
            payloads.map((payload) => action.execute(payload))
          );
      // create a map of players' ids and their statuses
      const idsToStatus = recipientStates.reduce(
        (obj, { recipient, status }) => {
          obj[getPlayerId(recipient)] = status;
          return obj;
        },
        {}
      );
      // determine statuses based on the response's return value
      for (const response of responses) {
        let result, player_id;
        // if fulfilled it also contains Response object as 'value` param
        if (response.status === "fulfilled" && response.value.ok) {
          result = await response.value.json();
          player_id = result.arguments.player_id;
          if (!result.failed) {
            idsToStatus[player_id] = ACTION_STATUS.success;
            // invalidate the player profile query
            queryClient.invalidateQueries({
              queryKey: ["player", "profile", player_id],
            });
          } else {
            allSuccess = false;
            idsToStatus[player_id] = ACTION_STATUS.error;
          }
          // otherwise it contains the error object as 'reason' param
        } else {
          allSuccess = false;
          // Change this if you want to obtain the message from the server
          // response.value = Response object
          setError(response.reason);
        }
      }
      // update UI
      setRecipientStates((prevStatePlayers) => {
        return prevStatePlayers.map((state) => {
          const { recipient } = state;
          let nextStatus =
            idsToStatus[getPlayerId(recipient)] !== ACTION_STATUS.success
              ? ACTION_STATUS.error
              : idsToStatus[getPlayerId(recipient)];

          return {
            ...state,
            status: nextStatus,
          };
        });
      });

      if (allSuccess) {
        setSuccess(true);
        setLoading(false);
      } else {
        setLoading(false);
      }
    },
    [
      action,
      params,
      queryClient,
      recipientStates,
      setError,
      setLoading,
      setSuccess,
    ]
  );

  const handleDeleteRecipient = (player) => {
    setRecipientStates((prev) =>
      prev.filter((label) => label.recipient.player_id !== player.player_id)
    );
  };

  const handleAddRecipient = (player) => {
    if (
      !recipientStates.some(
        (label) => label.recipient.player_id === player.player_id
      )
    ) {
      setRecipientStates((prev) => {
        return [...prev, ...initRecipients([player])];
      });
    }
  };

  const ActionFields = action.component;

  return (
    <Stack spacing={1}>
      <Box
        component="fieldset"
        disabled={locked}
        sx={{ border: 0, m: 0, minWidth: 0, p: 0 }}
      >
        <BadgeList
          recipients={recipientStates}
          onDelete={handleDeleteRecipient}
        />
        {recipients.length === 0 && (
          <PlayerSearchField onSelect={handleAddRecipient} />
        )}
      </Box>
      <form onSubmit={handleSubmit(onSubmit)}>
        <Box
          component="fieldset"
          disabled={locked}
          sx={{ border: 0, m: 0, minWidth: 0, p: 0 }}
        >
          <ActionFields errors={errors} {...formProps} {...actionState} />
        </Box>
        <Button
          ref={submitRef}
          type="submit"
          sx={{ display: submitRef && "none" }}
          disabled={!recipientStates || recipientStates.length === 0}
        >
          {t("common.submit")}
        </Button>
      </form>
    </Stack>
  );
};
