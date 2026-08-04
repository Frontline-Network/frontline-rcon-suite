import { TimePickerButtons } from "@/components/shared/TimePickerButtons";
import { ExpirationField } from "../fields/ExpirationField";
import { ForwardField } from "../fields/ForwardField";
import { Alert, Box, Button, Stack, TextField } from "@mui/material";
import dayjs from "dayjs";
import { ControlledTextInput } from "@/components/form/core/ControlledTextInput";
import { useTranslation } from "react-i18next";

const presetTimes = [
  [2, "hours"],
  [1, "day"],
  [1, "week"],
  [1, "month"],
];

export const AddVipFormFields = ({ control, errors, setValue, getValues }) => {
  const { t } = useTranslation();
  const expiration = getValues()?.expiration;
  return (
    <Stack gap={3}>
      <TextField
        label={t("fields.vipPreview")}
        value={
          (getValues()?.prefix ?? "") +
          "<Player>" +
          (getValues()?.suffix ?? "")
        }
        helperText={t("fields.vipPreviewHelp")}
        fullWidth
        disabled
      />
      <Stack direction={["column", "row"]} gap={1}>
        <ControlledTextInput
          control={control}
          errors={errors}
          // shouldValidate is needed to trigger rerendering
          // so the description field is updated
          onChange={(e) => setValue("prefix", e.target.value, { shouldValidate: true })}
          value={getValues()?.prefix ?? ""}
          name="prefix"
          label={t("fields.prefix")}
          placeholder="[TAG]"
          helperText={t("fields.prefixHelp")}
          sx={{ flex: 1 }}
        />
        <ControlledTextInput
          control={control}
          errors={errors}
          // shouldValidate is needed to trigger rerendering
          // so the description f is updated
          onChange={(e) => setValue("suffix", e.target.value, { shouldValidate: true })}
          value={getValues()?.suffix ?? ""}
          name="suffix"
          label={t("fields.suffix")}
          placeholder="[TAG]"
          helperText={t("fields.suffixHelp")}
          sx={{ flex: 1 }}
        />
      </Stack>
      {expiration !== null ? (
        <ExpirationField name="expiration" control={control} errors={errors} />
      ) : (
        <>
          <Alert severity="info">
            {t("fields.vipIndefinite")}
          </Alert>
          <input type="hidden" name="expiration" value={null} />
        </>
      )}
      <Box>
        <Button
          variant="outlined"
          size="small"
          color="secondary"
          style={{ display: "block", width: "100%", marginBottom: 4 }}
          onClick={() => setValue("expiration", dayjs().add(15, "minutes"))}
        >
          {t("fields.vipQueueHelp")}
        </Button>
        {presetTimes.map(([amount, unit], index) => (
          <TimePickerButtons
            key={unit + index}
            amount={amount}
            unit={unit}
            expirationTimestamp={getValues()?.expiration ?? dayjs()}
            // shouldValidate is needed to trigger rerendering
            // so the getValues()?.expiration is updated
            setExpirationTimestamp={(value) => {
              setValue("expiration", value, {
                shouldTouch: true,
                shouldValidate: true,
              });
            }}
          />
        ))}
        <Button
          variant="outlined"
          size="small"
          color="secondary"
          style={{ display: "block", width: "100%" }}
          onClick={() =>
            setValue("expiration", null, {
              shouldTouch: true,
              shouldValidate: true,
            })
          }
        >
          {t("fields.neverExpires")}
        </Button>
      </Box>
      <ForwardField control={control} errors={errors} />
    </Stack>
  );
};
