import { Suspense, useEffect, useMemo, useState } from "react";
import {
  Await,
  defer,
  useLoaderData,
  useNavigation,
  useSubmit,
} from "react-router-dom";
import { Autocomplete, Box, Skeleton, TextField } from "@mui/material";
import { useTranslation } from "react-i18next";
import "@fontsource/montserrat";
import { AsyncClientError } from "@/components/shared/AsyncClientError";
import { isFakeMode } from "@/mirage/demo-data";
import { cmd } from "@/utils/fetchUtils";
import { TEMPLATE_CATEGORY } from "@/utils/lib";
import WelcomeMessageWorkbench from "./WelcomeMessageWorkbench";

const INTENT = {
  APPLY_SINGLE: 0,
  APPLY_ALL: 1,
};

export const loader = async () => {
  if (isFakeMode()) {
    return defer({
      message:
        "Willkommen beim Frontline Network. Bitte beachte unsere Serverregeln.",
      templates: Promise.resolve([
        {
          id: 1,
          title: "FLN Willkommen",
          content: "Willkommen beim Frontline Network.",
          updated_at: new Date().toISOString(),
          updated_by: "Frontline Admin",
        },
      ]),
    });
  }

  const message = await cmd.GET_WELCOME_MESSAGE();
  const templates = cmd.GET_MESSAGE_TEMPLATES({
    params: { category: TEMPLATE_CATEGORY.WELCOME },
  });
  return defer({ message: message ?? "", templates });
};

export const action = async ({ request }) => {
  const payload = await request.json();
  return cmd.SET_WELCOME_MESSAGE({ payload });
};

const TemplateSkeleton = () => (
  <Box data-theme-surface="panel" sx={{ border: "1px solid", borderColor: "divider", p: 2 }}>
    <Skeleton height={54} />
    <Skeleton width="54%" />
  </Box>
);

export default function WelcomeMessagePage() {
  const { t } = useTranslation();
  const data = useLoaderData();
  const navigation = useNavigation();
  const submit = useSubmit();
  const [message, setMessage] = useState(data.message ?? "");
  const [activeSection, setActiveSection] = useState("messages");
  const saving = navigation.state !== "idle";

  useEffect(() => {
    setMessage(data.message ?? "");
  }, [data.message]);

  const hasChanges = useMemo(
    () => message !== (data.message ?? ""),
    [message, data.message]
  );

  const apply = (intent) => {
    submit(
      {
        forward: intent === INTENT.APPLY_ALL,
        message: !message.trim() ? null : message,
      },
      { method: "post", encType: "application/json" }
    );
  };

  const templatePicker = (
    <Suspense fallback={<TemplateSkeleton />}>
      <Await
        resolve={data.templates}
        errorElement={
          <AsyncClientError title={t("settings.welcome.templates")} />
        }
      >
        {(templates) => (
          <Autocomplete
            id="welcome-template-select"
            fullWidth
            options={templates}
            onChange={(_, template) => {
              if (!template) return;
              setMessage(template.content ?? "");
              setActiveSection("messages");
            }}
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
                helperText={t("settings.welcome.templatePickerHint")}
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
    <WelcomeMessageWorkbench
      message={message}
      activeSection={activeSection}
      onSectionChange={setActiveSection}
      onMessageChange={setMessage}
      onReset={() => setMessage(data.message ?? "")}
      onApply={() => apply(INTENT.APPLY_SINGLE)}
      onApplyAll={() => apply(INTENT.APPLY_ALL)}
      hasChanges={hasChanges}
      saving={saving}
      templatePicker={templatePicker}
    />
  );
}
