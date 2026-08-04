import {
  Box,
  Skeleton,
  Stack,
  Typography,
  useTheme,
} from "@mui/material";
import { ControlledTextInput } from "@/components/form/core/ControlledTextInput";
import { lazy, Suspense } from "react";
import { Controller } from "react-hook-form";
import emojiData from "@emoji-mart/data/sets/15/twitter.json";
import Emoji from "@/components/shared/Emoji";
import { useTranslation } from "react-i18next";

const EmojiPicker = lazy(() => import("@emoji-mart/react"));

export const AddFlagFormFields = ({ control, errors, setValue }) => {
  const { t } = useTranslation();
  const theme = useTheme();

  // It is called 'comment' at the backend but it is really a 'note' for the flag
  const noteError = errors["comment"];
  const hasNoteError = !!noteError;

  const flagError = errors["flag"];
  const hasFlagError = !!flagError;

  return (
    <Stack alignContent={"center"} spacing={2}>
      <Stack direction={"row"} spacing={1}>
        <Controller
          defaultValue={""}
          rules={{ required: t("fields.flagRequired") }}
          name={"flag"}
          control={control}
          render={({ field }) => (
            <>
              <Stack direction={"column"} alignItems={"start"} spacing={0.25}>
                <Box
                  sx={{
                    border: (theme) => `1px solid ${theme.palette.grey[500]}`,
                    px: 2,
                    py: 1.75,
                    color: (theme) => theme.palette.grey[400],
                    borderRadius: 1,
                    height: "3.5rem",
                    width: "6.5rem",
                    borderColor: (theme) =>
                      hasFlagError
                        ? theme.palette.error.main
                        : theme.palette.grey[500],
                  }}
                >
                  {field.value ? <Emoji emoji={field.value} size={24} /> : t("fields.flag")}
                </Box>
                <Typography
                  variant="caption"
                  sx={{ color: (theme) => hasFlagError ? theme.palette.error.main : theme.palette.grey[400], px: 1 }}
                >
                  {hasFlagError ? flagError.message : t("fields.emoji")}
                </Typography>
              </Stack>
              <input
                onChange={field.onChange} // send value to hook form
                onBlur={field.onBlur} // notify when input is touched/blur
                value={field.value} // input value
                name={field.name} // send down the input name
                hidden
              />
            </>
          )}
        />
        <ControlledTextInput
          control={control}
          error={hasNoteError}
          rows={1}
          label={t("fields.note")}
          name={"comment"}
          helperText={
            hasNoteError ? noteError.message : t("fields.noteHelp")
          }
          sx={{ flexGrow: 1 }}
          defaultValue={""}
        />
      </Stack>
      <Suspense
        fallback={<Skeleton variant="rectangular" height={400} width={300} />}
      >
        <Box sx={{ "& em-emoji-picker": { width: "100%" } }}>
          <EmojiPicker
            set="twitter"
            theme={theme.palette.mode}
            dynamicWidth={true}
            data={emojiData}
            onEmojiSelect={(emoji) => {
              setValue("flag", emoji.native, {
                shouldTouch: true,
                shouldValidate: true,
              });
            }}
          />
        </Box>
      </Suspense>
    </Stack>
  );
};
