import * as React from "react";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import {
  Alert,
  CircularProgress,
  IconButton,
  Stack,
  Tooltip,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { cmd } from "@/utils/fetchUtils";
import ErrorBrowser from "@/components/shared/ErrorBrowser";
import debug from "@/utils/debug";
import ThreePIcon from "@mui/icons-material/ThreeP";
import { MessageField } from "./fields/MessageField";
import { useTranslation } from "react-i18next";

const logger = debug("MESSAGE ALL DIALOG");

export default function MessageAllDialog() {
  const { t } = useTranslation();
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down("md"));

  const {
    mutate: messageAll,
    isPending,
    isSuccess,
    isError,
    error,
    reset,
  } = useMutation({
    mutationFn: async (data) =>
      cmd.MESSAGE_ALL_PLAYERS({
        payload: { message: data.message },
        throwRouteError: false,
      }),
    onMutate: async (variables) => {
      logger(
        "<START: Messaging all players>\n",
        "Content:\n",
        variables.message
      );
    },
    onSuccess: async () => {
      logger("<SUCCESS: Messaging all players>\n");
      setTimeout(handleDialogClose, 1250);
    },
    onError: async (error) => {
      console.error("<ERROR: Messaging all players>\n", error);
    },
  });

  const {
    handleSubmit,
    formState: { errors: formErrors },
    setValue,
    watch,
    control,
    ...formProps
  } = useForm({
    defaultValues: {
      reason: "",
    },
  });

  const handleDialogClickOpen = () => {
    reset();
    setValue("message", "");
    setDialogOpen(true);
  };

  const handleDialogClose = () => {
    setDialogOpen(false);
  };

  const handleFormSubmit = (data) => {
    // Handle the form submission with selected squads
    logger("Form data:", data);
    messageAll(data);
  };

  return (
    <React.Fragment>
      <Tooltip title={t("actions.messageAll")}>
        <span>
          <IconButton onClick={handleDialogClickOpen}>
            <ThreePIcon />
          </IconButton>
        </span>
      </Tooltip>
      <Dialog
        open={dialogOpen}
        fullScreen={fullScreen}
        onClose={handleDialogClose}
        fullWidth
        slotProps={{
          paper: {
            component: "form",
            onSubmit: handleSubmit(handleFormSubmit),
          },
        }}
      >
        <DialogTitle>{t("actions.messageAll")}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {t("actions.messageAllDescription")}
          </DialogContentText>
          <Stack spacing={2} marginTop={2}>
            {isError && (
              <ErrorBrowser
                errors={[
                  error?.message ??
                    t("errors.unexpected"),
                ]}
                onClose={() => {}}
              />
            )}
            {isSuccess && (
              <Alert severity="success">{t("actions.messageSent")}</Alert>
            )}
            <MessageField
              control={control}
              errors={formErrors}
              setValue={setValue}
              {...formProps}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleDialogClose} disabled={isPending}>
            {t("common.cancel")}
          </Button>
          {isPending ? (
            <Button disabled startIcon={<CircularProgress size={"1rem"} />}>
              {t("actions.sending")}
            </Button>
          ) : (
            <Button type="submit" disabled={isPending}>
              {t("common.confirm")}
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </React.Fragment>
  );
}
