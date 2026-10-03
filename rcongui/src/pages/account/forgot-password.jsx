import { useEffect, useRef, useState } from "react";
import {
  Alert,
  Button,
  LinearProgress,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { Link, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import SectionSurface from "@/components/shared/SectionSurface";
import RecoveryLayout from "./RecoveryLayout";
import { passwordRequest } from "./password-client.mjs";

export default function ForgotPassword() {
  const { t, i18n } = useTranslation();
  const [searchParams] = useSearchParams();
  const language = i18n.resolvedLanguage?.startsWith("de") ? "de" : "en";
  const [email, setEmail] = useState("");
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(() => searchParams.get("sent") === "1");
  const [issue, setIssue] = useState("");
  const [fieldError, setFieldError] = useState("");
  const [version, setVersion] = useState(0);
  const sending = useRef(false);
  const sentRef = useRef(null);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setIssue("");
    setSettings(null);
    passwordRequest({ mode: "request", language, signal: controller.signal })
      .then(({ ok, data }) => {
        if (controller.signal.aborted) return;
        if (
          ok &&
          typeof data?.available === "boolean" &&
          typeof data.csrf_token === "string"
        )
          setSettings(data);
        else setIssue("loadFailed");
      })
      .catch(() => {
        if (!controller.signal.aborted) setIssue("loadFailed");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [language, version]);
  useEffect(() => {
    if (sent) sentRef.current?.focus();
  }, [sent]);
  const submit = async (event) => {
    event.preventDefault();
    if (sending.current || !settings?.available) return;
    sending.current = true;
    setSubmitting(true);
    setIssue("");
    setFieldError("");
    try {
      const result = await passwordRequest({
        mode: "request",
        language,
        values: { email },
        csrfToken: settings.csrf_token,
      });
      if (result.ok && result.data?.sent === true) {
        setEmail("");
        setSent(true);
      } else if (result.status === 429) setIssue("rateLimited");
      else if (result.status === 503 && result.data?.error === "unavailable")
        setSettings({ ...settings, available: false });
      else if (result.status === 403) {
        setSettings(null);
        setIssue("csrf");
      } else if (
        result.status === 400 &&
        Array.isArray(result.data?.errors?.email)
      ) {
        setFieldError(
          result.data.errors.email
            .filter((value) => typeof value === "string")
            .join(" ")
        );
      } else setIssue("requestFailed");
    } catch {
      setIssue("requestFailed");
    } finally {
      sending.current = false;
      setSubmitting(false);
    }
  };
  return (
    <RecoveryLayout
      title={t("accountPassword.forgotTitle")}
      subtitle={t("accountPassword.forgotSubtitle")}
    >
      <SectionSurface sx={{ p: { xs: 2, md: 3 } }}>
        <Stack
          gap={2.5}
          component="form"
          onSubmit={submit}
          aria-label={t("accountPassword.forgotTitle")}
        >
          {loading && (
            <LinearProgress aria-label={t("accountPassword.loading")} />
          )}
          {sent ? (
            <>
              <Alert severity="success" ref={sentRef} tabIndex={-1}>
                {t("accountPassword.sent")}
              </Alert>
              <Typography variant="body2" color="text.secondary">
                {t("accountPassword.deliveryHelp")}
              </Typography>
            </>
          ) : (
            <>
              {issue && (
                <Alert severity="error">
                  {t("accountPassword." + issue)}
                  {["loadFailed", "csrf"].includes(issue) && (
                    <Button
                      onClick={() => setVersion((value) => value + 1)}
                      disabled={loading}
                    >
                      {t("accountPassword.retry")}
                    </Button>
                  )}
                </Alert>
              )}
              {settings && !settings.available && (
                <Alert severity="info">
                  {t("accountPassword.unavailable")}
                </Alert>
              )}
              <TextField
                id="recovery-email"
                name="email"
                type="email"
                label={t("accountPassword.email")}
                autoComplete="email"
                value={email}
                onChange={(event) => {
                  setEmail(event.target.value);
                  setFieldError("");
                }}
                disabled={loading || !settings?.available}
                inputProps={{ readOnly: submitting, maxLength: 254 }}
                required
                fullWidth
                error={Boolean(fieldError)}
                helperText={fieldError || t("accountPassword.emailHelp")}
              />
              <Button
                type="submit"
                variant="contained"
                disabled={submitting || loading || !settings?.available}
              >
                {t(
                  submitting
                    ? "accountPassword.sending"
                    : "accountPassword.send"
                )}
              </Button>
            </>
          )}
          <Button component={Link} to="/login" disabled={submitting}>
            {t("accountPassword.backToLogin")}
          </Button>
        </Stack>
      </SectionSurface>
    </RecoveryLayout>
  );
}
