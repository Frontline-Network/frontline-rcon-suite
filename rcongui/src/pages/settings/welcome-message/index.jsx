import {Suspense, useEffect, useMemo, useState} from "react";
import { Await, defer, Link, useLoaderData, useSubmit } from "react-router-dom";
import { cmd } from "@/utils/fetchUtils";
import { AsyncClientError } from "@/components/shared/AsyncClientError";
import {
  Autocomplete,
  Box,
  Button,
  Paper,
  Skeleton,
  Stack,
  TextField,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import "@fontsource/montserrat";
import SplitButton from "@/components/shared/SplitButton";
import AddCommentIcon from "@mui/icons-material/AddComment";
import { TEMPLATE_CATEGORY } from "@/utils/lib";
import { isFakeMode } from "@/mirage/demo-data";
import { useTranslation } from "react-i18next";
import PageHeader from "@/components/shared/PageHeader";
import ConfirmButton from "@/components/shared/ConfirmButton";

const INTENT = {
  APPLY_SINGLE: 0,
  APPLY_ALL: 1,
};

export const loader = async () => {
  if (isFakeMode()) {
    return defer({ message: "Willkommen beim Frontline Network. Bitte beachte unsere Serverregeln.", templates: Promise.resolve([{ id: 1, title: "FLN Willkommen", content: "Willkommen beim Frontline Network.", updated_at: new Date().toISOString(), updated_by: "Frontline Admin" }]) });
  }
  const message = await cmd.GET_WELCOME_MESSAGE();
  const templates = cmd.GET_MESSAGE_TEMPLATES({
    params: { category: TEMPLATE_CATEGORY.WELCOME },
  });
  return defer({ message: message ?? "", templates });
};

export const action = async ({ request }) => {
  const payload = await request.json();
  const result = await cmd.SET_WELCOME_MESSAGE({ payload });
  return result;
};

const TemplateSkeleton = () => <Skeleton height={80} />;

const WelcomeMessagePage = () => {
  const { t } = useTranslation();
  const data = useLoaderData();
  const submit = useSubmit();
  const [message, setMessage] = useState(data.message);
  const [loading, setLoading] = useState(false);
  const theme = useTheme();
  const compact = useMediaQuery(theme.breakpoints.down("md"));

  useEffect(() => {
    setMessage(data.message);
    setLoading(false);
  }, [data.message]);

  const handleOnChange = (event) => {
    setMessage(event.target.value);
  };

  const handleApplyClick = (intent) => (e) => {
    const payload = {
      forward: intent === INTENT.APPLY_ALL,
      // if only space chars, send null
      message: !message.trim() ? null : message,
    };
    submit(payload, { method: "post", encType: "application/json" });
  };

  const handleTemplateChange = (e, message) => {
    setMessage(message.content);
  };

  const hasChanges = useMemo(
    () => message !== data.message,
    [message, data.message]
  );

  const applyDisabled = loading || !hasChanges;

  return (
    <Box sx={{ maxWidth: (theme) => theme.breakpoints.values.lg, minWidth: 0, pb: { xs: 10, md: 0 } }}>
      <PageHeader
        eyebrow={t("settings.welcome.eyebrow")}
        title={t("settings.welcome.title")}
        subtitle={t("settings.welcome.subtitle")}
        actions={!compact ? (
          <Button
            component={Link}
            startIcon={<AddCommentIcon />}
            variant="outlined"
            to={"/settings/templates/" + TEMPLATE_CATEGORY.WELCOME.toLowerCase()}
          >
            {t("settings.broadcast.createTemplate")}
          </Button>
        ) : null}
      />
      <Suspense fallback={<TemplateSkeleton />}>
        <Await
          resolve={data.templates}
          errorElement={<AsyncClientError title={t("settings.welcome.templates")} />}
        >
          {(templates) => {
            return (
              <Autocomplete
                id="template-select"
                fullWidth
                options={templates}
                onChange={handleTemplateChange}
                autoHighlight
                getOptionLabel={(option) => option.title}
                renderOption={(props, option) => {
                  const { key, ...optionProps } = props;
                  return (
                    <Box key={key} component="li" {...optionProps}>
                      #{option.id} {option.title}
                    </Box>
                  );
                }}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label={t("settings.templates.select")}
                    slotProps={{
                      htmlInput: {
                        ...params.inputProps,
                      },
                    }}
                  />
                )}
              />
            );
          }}
        </Await>
      </Suspense>

      {compact && (
        <Button
          component={Link}
          startIcon={<AddCommentIcon />}
          variant="outlined"
          fullWidth
          to={"/settings/templates/" + TEMPLATE_CATEGORY.WELCOME.toLowerCase()}
          sx={{ mt: 1, minHeight: 44 }}
        >
          {t("settings.broadcast.createTemplate")}
        </Button>
      )}

      <Paper variant="outlined" sx={{ mt: 1.5, p: { xs: 1.5, sm: 2 }, borderRadius: 0 }}>
        <TextField
          name="message"
          value={message ?? ""}
          onChange={handleOnChange}
          placeholder={t("settings.templates.messageContent")}
          multiline
          minRows={compact ? 10 : 16}
          fullWidth
          required
          helperText={t("settings.welcome.editorHint")}
        />
      </Paper>

      {compact ? (
        <Stack
          component={Paper}
          direction="row"
          gap={1}
          sx={{
            position: "sticky",
            bottom: "calc(64px + env(safe-area-inset-bottom))",
            zIndex: theme.zIndex.appBar,
            p: 1,
            mt: 1.5,
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          <Button
            variant="contained"
            disabled={applyDisabled}
            onClick={handleApplyClick(INTENT.APPLY_SINGLE)}
            sx={{ flex: 1, minHeight: 44 }}
          >
            {loading ? t("common.loading") : t("settings.welcome.apply")}
          </Button>
          <ConfirmButton
            disabled={applyDisabled}
            onConfirm={handleApplyClick(INTENT.APPLY_ALL)}
            title={t("settings.welcome.applyAllTitle")}
            description={t("settings.welcome.applyAllDescription")}
            buttonText={t("settings.welcome.allServers")}
            buttonProps={{ variant: "outlined", sx: { minHeight: 44 } }}
          />
        </Stack>
      ) : (
        <Stack component={Paper} direction="row" justifyContent="flex-end" sx={{ p: 1, mt: 1.5 }}>
          <SplitButton
            disabled={applyDisabled}
            options={[
              { name: loading ? t("common.loading") : t("settings.welcome.apply"), buttonProps: { disabled: applyDisabled, onClick: handleApplyClick(INTENT.APPLY_SINGLE) } },
              { name: loading ? t("common.loading") : t("settings.welcome.applyAllServers"), buttonProps: { disabled: applyDisabled, onClick: handleApplyClick(INTENT.APPLY_ALL) } },
            ]}
          />
        </Stack>
      )}
    </Box>
  );
};

export default WelcomeMessagePage;
