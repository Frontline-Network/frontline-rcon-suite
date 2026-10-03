import Padlock from "@/components/shared/Padlock";
import SplitButton from "@/components/shared/SplitButton";
import ConfirmButton from "@/components/shared/ConfirmButton";
import PageHeader from "@/components/shared/PageHeader";
import { cmd } from "@/utils/fetchUtils";
import { TEMPLATE_CATEGORY } from "@/utils/lib";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Paper,
  Skeleton,
  TextField,
  Stack,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import { lazy, Suspense, useEffect, useState } from "react";
import {
  Await,
  defer,
  json,
  useActionData,
  useLoaderData,
  useSubmit,
} from "react-router-dom";
import { AsyncClientError } from "@/components/shared/AsyncClientError";
import { isFakeMode } from "@/mirage/demo-data";
import { useTranslation } from "react-i18next";

const Editor = lazy(() => import("@monaco-editor/react"));

const INTENT = {
  APPLY_SINGLE: "0",
  APPLY_ALL: "1",
  TOGGLE_SERVICE: "2",
};

export const loader = async () => {
  if (isFakeMode()) {
    return defer({
      service: { name: "auto_settings", statename: "RUNNING" },
      autosettings: { version: 1, enabled: true, rules: [] },
      templates: Promise.resolve([]),
    });
  }
  const autosettings = await cmd.GET_AUTOSETTINGS();
  const services = await cmd.GET_SERVICES();
  const templates = cmd.GET_MESSAGE_TEMPLATES({
    params: { category: TEMPLATE_CATEGORY.AUTO_SETTINGS },
  });
  return defer({
    service: services.find((service) => service.name === "auto_settings"),
    autosettings,
    templates,
  });
};

export const action = async ({ request }) => {
  const formData = Object.fromEntries(await request.formData());
  const { intent, ...data } = formData;
  let result;

  try {
    switch (intent) {
      case INTENT.APPLY_ALL:
      case INTENT.APPLY_SINGLE:
        result = await cmd.SET_AUTOSETTINGS({ payload: data });
        break;
      case INTENT.TOGGLE_SERVICE:
        result = await cmd.TOGGLE_SERVICE({ payload: data });
        break;
      default:
        return json(
          {
            error: "InvalidIntent",
          },
          { status: 400 }
        );
    }
  } catch (error) {
    let responseError = null;
    if (error instanceof Response) {
      responseError = await error
        .clone()
        .json()
        .catch(() => null);
    }
    return json(
      {
        error: {
          message:
            responseError?.message ||
            error?.message ||
            error?.text ||
            "Die Aktion konnte nicht ausgef\u00fchrt werden.",
          status: error?.status || 500,
        },
      },
      { status: 400 }
    );
  }

  return result;
};

const isRunning = (service) => service?.statename === "RUNNING";

const TemplateSkeleton = () => <Skeleton height={80} />;

const Autosettings = () => {
  const { t } = useTranslation();
  const data = useLoaderData();
  const [editorContent, setEditorContent] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const actionData = useActionData();
  const submit = useSubmit();
  const theme = useTheme();
  const compact = useMediaQuery(theme.breakpoints.down("md"));

  const handleApplyClick = (intent) => () => {
    setSubmitting(true);
    const formData = new FormData();
    formData.append("intent", intent);
    formData.append("forward", intent === INTENT.APPLY_ALL ? "true" : "false");
    formData.append("settings", editorContent);
    submit(formData, { method: "post" });
  };

  const handleToggleService = (checked) => {
    const formData = new FormData();
    formData.append("intent", INTENT.TOGGLE_SERVICE);
    formData.append("action", checked ? "start" : "stop");
    formData.append("service_name", "auto_settings");
    submit(formData, { method: "post" });
  };

  const handleTemplateChange = (e, message) => {
    setEditorContent(
      message ? message.content : JSON.stringify(data.autosettings, null, 2)
    );
  };

  useEffect(() => {
    if (!actionData?.error) {
      setEditorContent(JSON.stringify(data.autosettings, null, 2));
    }
  }, [data.autosettings, actionData]);

  useEffect(() => {
    setSubmitting(false);
    if (actionData) {
      if (actionData.error) {
        setError(actionData.error.message);
      } else {
        setError(null);
      }
    }
  }, [actionData]);

  const templatePicker = (
    <Suspense fallback={<TemplateSkeleton />}>
      <Await
        resolve={data.templates}
        errorElement={
          <AsyncClientError title={t("settings.autosettings.templates")} />
        }
      >
        {(templates) => (
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
        )}
      </Await>
    </Suspense>
  );

  return (
    <Stack
      className="wardogs-autosettings"
      gap={compact ? 1.25 : 2}
      sx={{ minWidth: 0, pb: { xs: 2, md: 0 } }}
    >
      <PageHeader
        eyebrow={t("settings.autosettings.eyebrow")}
        title={t("settings.autosettings.title")}
        subtitle={t("settings.autosettings.subtitle")}
      />
      <Stack
        component={Paper}
        sx={{ p: { xs: 1.25, md: 1 }, mb: { xs: 0, md: 1 } }}
        direction={{ xs: "column", md: "row" }}
        justifyContent={"space-between"}
        gap={1}
      >
        <Padlock
          label={t(
            isRunning(data.service) ? "common.enabled" : "common.disabled"
          )}
          checked={isRunning(data.service)}
          handleChange={handleToggleService}
        />
        <Stack direction={{ xs: "column", md: "row" }} gap={1}>
          <Button
            variant={compact ? "outlined" : "contained"}
            color="secondary"
            href="https://github.com/MarechJ/hll_rcon_tool/wiki/User-Guide-%E2%80%90-Main-interface-%E2%80%90-Settings-%E2%80%90-Autosettings"
            component={"a"}
            sx={{ minHeight: 44 }}
          >
            {t("settings.autosettings.readDocs")}
          </Button>
          {!compact ? (
            <SplitButton
              disabled={submitting}
              options={[
                {
                  name: submitting
                    ? t("common.processing")
                    : t("settings.autosettings.apply"),
                  buttonProps: {
                    onClick: handleApplyClick(INTENT.APPLY_SINGLE),
                    disabled: submitting,
                  },
                },
                {
                  name: submitting
                    ? t("common.processing")
                    : t("settings.autosettings.applyAllServers"),
                  buttonProps: {
                    onClick: handleApplyClick(INTENT.APPLY_ALL),
                    disabled: submitting,
                  },
                },
              ]}
            />
          ) : null}
        </Stack>
      </Stack>
      {error && <Alert severity="error">{error}</Alert>}
      {compact ? templatePicker : null}
      <Box
        component="section"
        aria-labelledby="autosettings-editor-title"
        sx={{ minWidth: 0 }}
      >
        {compact ? (
          <Stack spacing={0.25} sx={{ mb: 0.75 }}>
            <Typography
              id="autosettings-editor-title"
              component="h2"
              variant="subtitle1"
            >
              {t("settings.autosettings.editorTitle")}
            </Typography>
            <Typography color="text.secondary" variant="caption">
              {t("settings.autosettings.editorHint")}
            </Typography>
          </Stack>
        ) : null}
        <Box data-theme-surface="panel"
          sx={{
            border: (themeValue) => `1px solid ${themeValue.palette.divider}`,
            minWidth: 0,
            overflow: "hidden",
            width: "100%",
          }}
        >
          <Suspense>
            <Editor
              height={compact ? "clamp(320px, 50dvh, 520px)" : "70vh"}
              defaultLanguage="json"
              value={editorContent}
              defaultValue=""
              theme={theme.palette.mode === "dark" ? "vs-dark" : "vs-light"}
              onChange={(value) => setEditorContent(value)}
              options={{
                minimap: { enabled: !compact },
                wordWrap: compact ? "on" : "off",
                lineNumbersMinChars: compact ? 2 : 5,
                padding: { top: 8, bottom: 8 },
              }}
            />
          </Suspense>
        </Box>
      </Box>
      {!compact ? templatePicker : null}
      {compact ? (
        <Stack data-theme-surface="panel"
          component={Paper}
          elevation={6}
          spacing={1}
          sx={{
            bottom: "calc(64px + env(safe-area-inset-bottom, 0px))",
            border: (themeValue) => `1px solid ${themeValue.palette.divider}`,
            p: 1,
            position: "sticky",
            zIndex: (themeValue) => themeValue.zIndex.appBar - 1,
          }}
        >
          <Button
            variant="contained"
            disabled={submitting}
            onClick={handleApplyClick(INTENT.APPLY_SINGLE)}
            sx={{ minHeight: 48 }}
          >
            {submitting
              ? t("common.processing")
              : t("settings.autosettings.apply")}
          </Button>
          <ConfirmButton
            disabled={submitting}
            onConfirm={handleApplyClick(INTENT.APPLY_ALL)}
            title={t("settings.autosettings.applyAllTitle")}
            description={t("settings.autosettings.applyAllDescription")}
            buttonText={t("settings.autosettings.applyAllServers")}
            buttonProps={{
              color: "secondary",
              variant: "outlined",
              fullWidth: true,
              sx: { minHeight: 44 },
            }}
          />
        </Stack>
      ) : null}
    </Stack>
  );
};

export default Autosettings;
