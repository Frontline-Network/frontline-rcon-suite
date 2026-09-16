import { isRouteErrorResponse } from "react-router-dom";
import { useRouteError, useLocation } from "react-router-dom";
import { Stack, Typography, Button, Paper } from "@mui/material";
import { Link } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faDiscord } from "@fortawesome/free-brands-svg-icons/faDiscord";
import siteConfig from "@/config/siteConfig";
import { useTranslation } from "react-i18next";
import { useEffect } from "react";
import { translateOperatorMessage } from "@/i18n/operator-messages";

const staleBundleErrorPattern =
  /failed to fetch dynamically imported module|importing a module script failed|chunkloaderror|\(\s*0\s*,\s*[\w$]+\.isFunction\s*\)\s*is not a function/i;
const chunkReloadKeyPrefix = "crcon.chunk-load-retry:";

const getChunkReloadKey = (errorDetail) => {
  const assetUrl = errorDetail.match(/\/assets\/[^\s)]+\.js/i)?.[0];
  return `${chunkReloadKeyPrefix}${assetUrl ?? errorDetail}`;
};

export default function RouteError() {
  const { t } = useTranslation();
  const error = useRouteError();
  const location = useLocation();
  const errorDetail =
    error?.statusText ||
    error?.message ||
    error?.data?.message ||
    error?.data?.text ||
    (typeof error?.data === "string" ? error.data : "") ||
    (() => {
      try {
        return JSON.stringify(error);
      } catch {
        return String(error ?? "");
      }
    })();
  const normalizedErrorDetail = String(errorDetail ?? "");
  const isStaleBundleError = staleBundleErrorPattern.test(
    normalizedErrorDetail
  );

  useEffect(() => {
    if (!isStaleBundleError) return;

    const reloadKey = getChunkReloadKey(normalizedErrorDetail);
    try {
      if (window.sessionStorage.getItem(reloadKey)) return;
      window.sessionStorage.setItem(reloadKey, "1");
      window.location.reload();
    } catch {
      // If session storage is not available, keep the error visible instead of
      // risking a reload loop.
    }
  }, [isStaleBundleError, normalizedErrorDetail]);

  console.error(error);
  if (
    isRouteErrorResponse(error) &&
    error.status >= 400 &&
    error.status < 500
  ) {
    const errorData = error.data;
    const errorMessage =
      (typeof errorData === "object" && errorData !== null
        ? errorData.text ?? errorData.message
        : errorData) ?? error.statusText;
    const errorCommand =
      typeof errorData === "object" && errorData !== null
        ? errorData.command
        : null;
    const errorName =
      typeof errorData === "object" && errorData !== null
        ? errorData.name ?? errorData.error
        : null;
    // the response json is automatically parsed to
    // `error.data`, you also have access to the status
    return (
      <Stack spacing={2} alignItems={"center"} justifyContent={"center"}>
        <Typography variant="h3">{error.status}</Typography>
        <Typography variant="h4">{String(translateOperatorMessage(errorMessage, t) ?? "")}</Typography>
        {errorCommand ? <Typography>{String(errorCommand)}</Typography> : null}
        {errorName ? <Typography>{String(errorName)}</Typography> : null}
        <Button variant="contained" LinkComponent={Link} to={location.pathname}>
          {t("errors.tryAgain")}
        </Button>
      </Stack>
    );
  }

  return (
    <Stack
      id="error-page"
      spacing={2}
      alignItems={"center"}
      justifyContent={"center"}
      sx={{ textAlign: "center" }}
    >
      <Typography
        variant="overline"
        color="primary.main"
        sx={{ fontWeight: 800, letterSpacing: "0.14em" }}
      >
        Frontline Network
      </Typography>
      <Typography variant="h2">{t("errors.title")}</Typography>
      <Typography variant="h2">{t("errors.unexpected")}</Typography>
      <Typography variant="h3">{t("errors.persistent")}</Typography>
      <Paper elevation={4} variant="outlined" sx={{ padding: 2 }}>
        <Typography variant="h4">
          {error.name ?? t("errors.unknown")}
        </Typography>
        <Typography variant="body1">
          <i>{translateOperatorMessage(errorDetail, t)}</i>
        </Typography>
      </Paper>
      <Stack direction={"row"} spacing={2}>
        <Button
          variant="contained"
          color="error"
          LinkComponent={"a"}
          href={siteConfig.bugReportChannelUrl}
          startIcon={<FontAwesomeIcon icon={faDiscord} />}
        >
          {t("errors.report")}
        </Button>
        <Button variant="contained" LinkComponent={Link} to={location.pathname}>
          {t("errors.back")}
        </Button>
      </Stack>
    </Stack>
  );
}
