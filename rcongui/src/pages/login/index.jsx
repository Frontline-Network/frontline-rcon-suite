import Button from "@mui/material/Button";
import CssBaseline from "@mui/material/CssBaseline";
import TextField from "@mui/material/TextField";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Container from "@mui/material/Container";
import { Alert, Stack } from "@mui/material";
import {
  Form,
  useSubmit,
  useActionData,
  useLoaderData,
} from "react-router-dom";
import { useForm, Controller } from "react-hook-form";
import { styled } from "@mui/material/styles";
import { redirect } from "react-router-dom";
import { cmd } from "@/utils/fetchUtils";
import {useEffect, useState} from "react";
import { useTranslation } from "react-i18next";
import FrontlineBrand from "@/components/layout/FrontlineBrand";
import LanguageSelector from "@/components/layout/LanguageSelector";

export const loader = async ({ request }) => {
  let user;
  const url = new URL(request.url);
  const from = url.searchParams.get("from") || "/";
  const sessionExpired = url.searchParams.get("session_expired") === "1";

  try {
    user = await cmd.IS_AUTHENTICATED({ throwRouteError: false });
  } catch (error) {

    if (error.status === 401) {
      return {
        error: error.name,
        messageKey: sessionExpired ? "login.sessionExpired" : "login.invalid",
        from,
      };
    }

    if (error.status === 500) {
      return {
        error: error.name,
        messageKey: "login.unavailable",
      };
    }

    return {
      error: error,
      messageKey: "login.unknownError",
    };
  }

  if (user.authenticated) {
    return redirect(from);
  }

  return {
    authenticated: user.authenticated,
    from,
    ...(sessionExpired
      ? { error: "session_expired", messageKey: "login.sessionExpired" }
      : {}),
  };
};

export const action = async ({ request }) => {
  const formData = await request.formData();
  const { username, password } = Object.fromEntries(formData);
  const from = formData.get("from") || "/";
  let isAuth = false;

  try {
    const { result } = await cmd.AUTHENTICATE({
      payload: {
        username: username,
        password: password,
      },
      throwRouteError: false,
    });
    isAuth = result;
  } catch (error) {
    if (error.status === 401) {
      return {
        error: error.name,
        messageKey: "login.invalid",
      };
    }

    if (error.status === 500) {
      return {
        error: error.name,
        messageKey: "login.unavailable",
      };
    }

    console.error(error)
    return {
      error: error,
      messageKey: "login.unknownError",
    };
  }

  if (isAuth) {
    return redirect(from);
  }
};

const Wrapper = styled(Box)(({ theme }) => ({
  position: "relative",
  minHeight: "100vh",
  height: "100%",
  display: "flex",
  flexDirection: "column",
  [theme.breakpoints.up("md")]: {
    flexDirection: "row",
  },
}));

const HeroImageWrapper = styled(Box)(({ theme }) => ({
  flexBasis: "33vh",
  height: "100%",
  [theme.breakpoints.up("md")]: {
    flexBasis: "60%",
  },
}));

const HeroImage = styled("img")(({ theme }) => ({
  position: "absolute",
  top: 0,
  left: 0,
  objectFit: "cover",
  width: "100%",
  height: "33%",
  filter: "saturate(0.72) contrast(1.08) brightness(0.72)",
  [theme.breakpoints.up("md")]: {
    height: "100%",
    width: "60%",
  },
}));

const MainWrapper = styled(Stack)(({ theme }) => ({
  flexBasis: "67vh",
  position: "relative",
  backgroundColor: theme.palette.background.default,
  [theme.breakpoints.up("md")]: {
    flexBasis: "40%",
  },
}));

export default function Login() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);

  const {
    handleSubmit,
    control,
    formState: { errors },
  } = useForm({
    defaultValues: {
      username: "",
      password: "",
    },
  });

  const authError = useActionData();
  const data = useLoaderData();
  const { from } = useLoaderData();

  const submit = useSubmit();

  useEffect(() => setLoading(false), [authError]);

  useEffect(() => {
    document.title = t("login.documentTitle");
  }, [t]);

  const onSubmit = (values, e) => {
    setLoading(true);
    submit(e.target);
  };

  return (
    <>
      <HeroImage src="/frontline-ops-night.png" alt="" />
      <Wrapper>
        <HeroImageWrapper>
          <Stack
            sx={{
              display: { xs: "none", md: "flex" },
              position: "absolute",
              left: "clamp(28px, 5vw, 80px)",
              bottom: "clamp(36px, 7vh, 90px)",
              maxWidth: 460,
              zIndex: 1,
            }}
            spacing={1.5}
          >
            <Typography variant="caption" color="primary.light" sx={{ textTransform: "uppercase" }}>{t("login.eyebrow")}</Typography>
            <Typography variant="h2" sx={{ textTransform: "uppercase" }}>Frontline Network</Typography>
            <Typography color="text.secondary" sx={{ maxWidth: 420 }}>{t("login.intro")}</Typography>
          </Stack>
        </HeroImageWrapper>
        <MainWrapper>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ p: 2 }}>
            <FrontlineBrand compact />
            <LanguageSelector />
          </Stack>
          <Container
            component="main"
            maxWidth="xs"
            sx={{ flexGrow: 1, display: "flex" }}
          >
            <CssBaseline />
            <Box
              sx={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Typography component="h1" variant="h3" sx={{ alignSelf: "stretch", textTransform: "uppercase" }}>
                {t("login.title")}
              </Typography>
              {data.error ? (
                <Box sx={{ py: 2, width: "100%" }}>
                  <Alert severity="error">{t(data.messageKey || "login.unknownError")}</Alert>
                </Box>
              ) : authError && !loading ? (
                <Box sx={{ py: 2, width: "100%" }}>
                  <Alert severity="error">{t(authError.messageKey || "login.unknownError")}</Alert>
                </Box>
              ) : null}
              <Form method="POST" onSubmit={handleSubmit(onSubmit)}>
                <input type="hidden" name="from" value={from} />
                <Controller
                  control={control}
                  name={"username"}
                  rules={{ required: t("login.usernameRequired") }}
                  render={({ field }) => (
                    <TextField
                      onChange={field.onChange}
                      onBlur={field.onBlur}
                      value={field.value}
                      name={field.name}
                      inputRef={field.ref}
                      id="username"
                      label={t("login.username")}
                      margin="normal"
                      helperText={errors["username"]?.message}
                      error={!!errors["username"]}
                      autoComplete="username"
                      fullWidth
                    />
                  )}
                />
                <Controller
                  control={control}
                  name={"password"}
                  rules={{ required: t("login.passwordRequired") }}
                  render={({ field }) => (
                    <TextField
                      onChange={field.onChange}
                      onBlur={field.onBlur}
                      value={field.value}
                      name={field.name}
                      inputRef={field.ref}
                      id="password"
                      type="password"
                      label={t("login.password")}
                      margin="normal"
                      helperText={errors["password"]?.message}
                      error={!!errors["password"]}
                      autoComplete="current-password"
                      fullWidth
                    />
                  )}
                />
                <Button
                  type="submit"
                  disabled={loading}
                  fullWidth
                  variant="contained"
                  sx={{ mt: 3, mb: 2 }}
                >
                  {loading ? t("login.submitting") : t("login.submit")}
                </Button>
              </Form>
            </Box>
          </Container>
          <Stack justifyContent={"end"} sx={{ px: 3, pb: 2 }}>
            <Typography variant="caption" color="text.secondary">Frontline Network · CRCON</Typography>
          </Stack>
        </MainWrapper>
      </Wrapper>
    </>
  );
}
