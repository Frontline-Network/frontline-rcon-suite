import { useEffect, useRef, useState } from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Divider,
  IconButton,
  InputAdornment,
  LinearProgress,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import VisibilityOffOutlinedIcon from "@mui/icons-material/VisibilityOffOutlined";
import { Link, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import SectionSurface from "@/components/shared/SectionSurface";
import { passwordLanguage, passwordRequest } from "./password-client.mjs";

const emptyValues = () => ({
  old_password: "",
  new_password1: "",
  new_password2: "",
});
const allFields = [
  ["old_password", "current", "current-password"],
  ["new_password1", "new", "new-password"],
  ["new_password2", "repeat", "new-password"],
];

export default function PasswordForm({ mode = "change", uid }) {
  const { t, i18n } = useTranslation();
  const [searchParams] = useSearchParams();
  const language = passwordLanguage(i18n.resolvedLanguage);
  const resetting = mode === "reset";
  const fields = resetting ? allFields.slice(1) : allFields;
  const [changed, setChanged] = useState(
    () => !resetting && searchParams.get("changed") === "1"
  );
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [version, setVersion] = useState(0);
  const [values, setValues] = useState(emptyValues);
  const [visible, setVisible] = useState({});
  const [errors, setErrors] = useState({});
  const [issue, setIssue] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const submittingRef = useRef(false);
  const inputRefs = useRef({});
  const successRef = useRef(null);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setSettings(null);
    setIssue("");
    passwordRequest({ language, mode, uid, signal: controller.signal })
      .then(({ ok, status, data }) => {
        if (controller.signal.aborted) return;
        if (status === 401) setIssue("sessionExpired");
        else if (data?.error === "invalid_link") setIssue("invalidLink");
        else if (
          !ok ||
          typeof data?.csrf_token !== "string" ||
          !data.csrf_token ||
          typeof data?.can_change_password !== "boolean"
        )
          setIssue("loadFailed");
        else setSettings(data);
      })
      .catch(() => {
        if (!controller.signal.aborted) setIssue("loadFailed");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [language, mode, uid, version]);

  useEffect(() => {
    if (changed) successRef.current?.focus();
  }, [changed]);

  const submit = async (event) => {
    event.preventDefault();
    if (
      submittingRef.current ||
      !settings?.csrf_token ||
      !settings.can_change_password
    )
      return;
    setErrors({});
    setIssue("");
    if (values.new_password1 !== values.new_password2) {
      setErrors({ new_password2: [t("accountPassword.mismatch")] });
      inputRefs.current.new_password2?.focus();
      return;
    }
    submittingRef.current = true;
    setSubmitting(true);
    setVisible({});
    const submitted = { ...values };
    setValues(emptyValues());
    try {
      const result = await passwordRequest({
        language,
        mode,
        uid,
        values: submitted,
        csrfToken: settings.csrf_token,
      });
      if (result.ok && result.data?.changed === true) setChanged(true);
      else if (result.data?.error === "invalid_link") setIssue("invalidLink");
      else if (result.status === 400 && result.data?.errors) {
        const next = Object.fromEntries(
          Object.entries(result.data.errors)
            .filter(([, messages]) => Array.isArray(messages))
            .map(([name, messages]) => [
              name,
              messages.filter((message) => typeof message === "string"),
            ])
        );
        setErrors(next);
        setIssue("validation");
        inputRefs.current[
          fields.find(([name]) => next[name])?.[0] || fields[0][0]
        ]?.focus();
      } else if (result.status === 401) setIssue("sessionExpired");
      else if (result.status === 403) {
        setSettings(null);
        setIssue("csrf");
      } else if (result.status === 429) setIssue("rateLimited");
      else setIssue("saveFailed");
    } catch {
      setIssue("saveFailed");
    } finally {
      Object.keys(submitted).forEach((key) => {
        submitted[key] = "";
      });
      submittingRef.current = false;
      setSubmitting(false);
    }
  };

  if (changed)
    return (
      <SectionSurface sx={{ p: { xs: 2, md: 3 }, maxWidth: 700 }}>
        <Stack gap={2}>
          <Alert severity="success" ref={successRef} tabIndex={-1}>
            {t("accountPassword.success")}
          </Alert>
          <Typography color="text.secondary">
            {t(
              resetting
                ? "accountPassword.resetSuccess"
                : "accountPassword.sessionInfo"
            )}
          </Typography>
          <Button
            component={Link}
            to={resetting ? "/login" : "/"}
            variant="contained"
            sx={{ alignSelf: "flex-start" }}
          >
            {t(resetting ? "accountPassword.login" : "accountPassword.back")}
          </Button>
        </Stack>
      </SectionSurface>
    );

  return (
    <>
      {loading && (
        <LinearProgress
          aria-label={t("accountPassword.loading")}
          sx={{ mb: 2 }}
        />
      )}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "minmax(0, 1fr)",
            lg: "minmax(0, 1.4fr) minmax(260px, 1fr)",
          },
          gap: 3,
          alignItems: "start",
        }}
      >
        <SectionSurface sx={{ p: { xs: 2, md: 3 } }}>
          <Stack
            component="form"
            onSubmit={submit}
            gap={2.5}
            aria-label={t(
              resetting
                ? "accountPassword.resetTitle"
                : "sidebar.changePassword"
            )}
          >
            <Stack direction="row" gap={1.5} alignItems="center">
              <LockOutlinedIcon color="primary" />
              <Box>
                <Typography component="h2" variant="h6">
                  {t("accountPassword.title")}
                </Typography>
                {settings?.username && (
                  <Typography variant="body2" color="text.secondary">
                    {t("accountPassword.account", {
                      username: settings.username,
                    })}
                  </Typography>
                )}
              </Box>
            </Stack>
            {issue && (
              <Alert severity="error">
                {t("accountPassword." + issue)}
                {issue === "sessionExpired" && (
                  <Button
                    component={Link}
                    to="/login?from=%2Faccount%2Fpassword"
                  >
                    {t("accountPassword.login")}
                  </Button>
                )}
                {issue === "invalidLink" && (
                  <Button component={Link} to="/forgot-password">
                    {t("accountPassword.requestNew")}
                  </Button>
                )}
                {["loadFailed", "csrf"].includes(issue) && (
                  <Button
                    disabled={loading}
                    onClick={() => setVersion((value) => value + 1)}
                  >
                    {t("accountPassword.retry")}
                  </Button>
                )}
              </Alert>
            )}
            {settings && !settings.can_change_password && (
              <Alert severity="info">{t("accountPassword.unusable")}</Alert>
            )}
            {issue !== "invalidLink" && (
              <>
                <input
                  type="text"
                  name="username"
                  autoComplete="username"
                  value={settings?.username || ""}
                  readOnly
                  hidden
                />
                {fields.map(([name, label, autocomplete]) => (
                  <TextField
                    key={name}
                    id={"account-" + name}
                    name={name}
                    inputRef={(node) => {
                      inputRefs.current[name] = node;
                    }}
                    label={t("accountPassword." + label)}
                    type={visible[name] ? "text" : "password"}
                    autoComplete={autocomplete}
                    value={values[name]}
                    onChange={(event) => {
                      setValues((current) => ({
                        ...current,
                        [name]: event.target.value,
                      }));
                      setErrors((current) => ({ ...current, [name]: [] }));
                    }}
                    required
                    fullWidth
                    disabled={loading || !settings?.can_change_password}
                    error={Boolean(errors[name]?.length)}
                    helperText={
                      errors[name]?.join(" ") ||
                      (name === "old_password"
                        ? t("accountPassword.currentHelp")
                        : undefined)
                    }
                    inputProps={{
                      readOnly: submitting,
                      spellCheck: false,
                      autoCapitalize: "none",
                    }}
                    InputProps={{
                      endAdornment: (
                        <InputAdornment position="end">
                          <IconButton
                            type="button"
                            edge="end"
                            disabled={
                              submitting || !settings?.can_change_password
                            }
                            aria-label={t(
                              visible[name]
                                ? "accountPassword.hide"
                                : "accountPassword.show",
                              { field: t("accountPassword." + label) }
                            )}
                            aria-pressed={Boolean(visible[name])}
                            onMouseDown={(event) => event.preventDefault()}
                            onClick={() =>
                              setVisible((current) => ({
                                ...current,
                                [name]: !current[name],
                              }))
                            }
                          >
                            {visible[name] ? (
                              <VisibilityOffOutlinedIcon />
                            ) : (
                              <VisibilityOutlinedIcon />
                            )}
                          </IconButton>
                        </InputAdornment>
                      ),
                    }}
                  />
                ))}
                {errors.__all__?.map((message) => (
                  <Alert key={message} severity="error">
                    {message}
                  </Alert>
                ))}
                <Divider />
                <Stack direction={{ xs: "column", sm: "row" }} gap={1.5}>
                  <Button
                    type="submit"
                    variant="contained"
                    disabled={
                      submitting || loading || !settings?.can_change_password
                    }
                    startIcon={
                      submitting ? (
                        <CircularProgress size={16} color="inherit" />
                      ) : null
                    }
                  >
                    {t(
                      submitting
                        ? "accountPassword.saving"
                        : "accountPassword.save"
                    )}
                  </Button>
                  <Button
                    component={Link}
                    to={resetting ? "/login" : "/"}
                    disabled={submitting}
                  >
                    {t("accountPassword.cancel")}
                  </Button>
                </Stack>
              </>
            )}
          </Stack>
        </SectionSurface>
        <Box component="aside" sx={{ p: { xs: 1, lg: 2 }, minWidth: 0 }}>
          <Typography component="h2" variant="subtitle1" sx={{ mb: 1 }}>
            {t("accountPassword.requirements")}
          </Typography>
          {Array.isArray(settings?.requirements) &&
          settings.requirements.length > 0 ? (
            <Box
              component="ul"
              sx={{
                pl: 2.5,
                mt: 0,
                color: "text.secondary",
                "& li": { mb: 1.5, lineHeight: 1.6, fontSize: "0.875rem" },
              }}
            >
              {settings.requirements
                .filter((text) => typeof text === "string")
                .map((text) => (
                  <li key={text}>{text}</li>
                ))}
            </Box>
          ) : (
            <Typography variant="body2" color="text.secondary">
              {t("accountPassword.recommendation")}
            </Typography>
          )}
          <Divider sx={{ my: 2.5 }} />
          <Typography component="h2" variant="subtitle1" sx={{ mb: 1 }}>
            {t("accountPassword.sessions")}
          </Typography>
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ lineHeight: 1.7 }}
          >
            {t(
              resetting
                ? "accountPassword.resetSessionInfo"
                : "accountPassword.sessionInfo"
            )}
          </Typography>
        </Box>
      </Box>
    </>
  );
}
