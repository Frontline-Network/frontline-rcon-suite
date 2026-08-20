import * as React from "react";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import ListItemButton from "@mui/material/ListItemButton";
import {
  Divider,
  Stack,
  Typography,
  IconButton,
  Skeleton,
  useTheme,
  useMediaQuery,
} from "@mui/material";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faDiscord } from "@fortawesome/free-brands-svg-icons/faDiscord";
import { faGithub } from "@fortawesome/free-brands-svg-icons/faGithub";
import { faBook } from "@fortawesome/free-solid-svg-icons/faBook";
import { faCircleQuestion } from "@fortawesome/free-solid-svg-icons/faCircleQuestion";
import siteConfig from "@/config/siteConfig";
import { cmd } from "@/utils/fetchUtils";
import { useQuery } from "@tanstack/react-query";
import dayjs from "dayjs";
import { useGithubReleases } from "@/hooks/useGithubReleases";
import RefreshIcon from "@mui/icons-material/Refresh";
import { Suspense } from "react";
import { HIGHLIGHT } from "./utils";
import { useTranslation } from "react-i18next";

const ReleaseNotes = React.lazy(() =>
  import("./ReleaseNotes").then((module) => ({
    default: module.ReleaseNotes,
  }))
);

const isNewerVersion = (a, b) => {
  const [aMajor, aMinor, aPatch] = a.split(".");
  const [bMajor, bMinor, bPatch] = b.split(".");
  return aMajor >= bMajor && aMinor >= bMinor && aPatch >= bPatch;
};

export default function AboutDialog() {
  const { t } = useTranslation();
  const [open, setOpen] = React.useState(false);
  const { releases, lastUpdate, unreadCount, markAsRead, forceUpdate } =
    useGithubReleases();
  const theme = useTheme();
  const isSmallScreen = useMediaQuery(theme.breakpoints.down("md"));

  const { data: apiVersion, isLoading } = useQuery({
    queryKey: ["apiVersion"],
    queryFn: cmd.GET_VERSION,
    initialData: "0.0.0",
  });

  const handleClickOpen = () => {
    markAsRead();
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
  };

  const descriptionElementRef = React.useRef(null);
  React.useEffect(() => {
    if (open) {
      const { current: descriptionElement } = descriptionElementRef;
      if (descriptionElement !== null) {
        descriptionElement.focus();
      }
    }
  }, [open]);

  const latestReleaseVersion =
    (releases?.[0]?.tag_name || releases?.[0]?.name) ?? "";
  const isUpToDate = isNewerVersion(
    apiVersion.trim(),
    latestReleaseVersion.trim()
  );

  return (
    <React.Fragment>
      <ListItem
        disablePadding
        onClick={handleClickOpen}
        sx={{
          height: 24,
          "& .MuiListItemText-root .MuiListItemText-primary": {
            fontSize: "0.75rem",
          },
        }}
      >
        <ListItemButton sx={{ marginLeft: 0.5 }}>
          <ListItemText
            primary={
              <Stack
                direction={"row"}
                justifyContent={"space-between"}
                alignItems={"center"}
              >
                <Stack alignItems={"center"} direction={"row"} gap={0.5}>
                  <FontAwesomeIcon
                    icon={faCircleQuestion}
                    color={unreadCount > 0 ? HIGHLIGHT.danger : ""}
                  />
                  Version: {apiVersion}
                </Stack>
              </Stack>
            }
          />
        </ListItemButton>
      </ListItem>
      <Dialog
        open={open}
        onClose={handleClose}
        aria-labelledby="about-dialog-title"
        aria-describedby="about-dialog-description"
        fullWidth
        fullScreen={isSmallScreen}
        maxWidth={"md"}
      >
        <DialogTitle id="about-dialog-title">{t("about.title")}</DialogTitle>
        <DialogContent dividers={true}>
          <Stack direction={["column", "row"]} gap={2} sx={{ mb: 2 }}>
            <Button
              size="small"
              variant="contained"
              LinkComponent="a"
              href={siteConfig.documentationUrl}
              target="_blank"
              startIcon={<FontAwesomeIcon icon={faBook} />}
            >
              {t("about.documentation")}
            </Button>
            <Button
              size="small"
              variant="contained"
              LinkComponent="a"
              href={siteConfig.discordUrl}
              target="_blank"
              startIcon={<FontAwesomeIcon icon={faDiscord} />}
            >
              {t("about.help")}
            </Button>
            <Button
              size="small"
              variant="contained"
              LinkComponent="a"
              href={siteConfig.githubUrl}
              target="_blank"
              startIcon={<FontAwesomeIcon icon={faGithub} />}
            >
              {t("about.issue")}
            </Button>
          </Stack>

          <DialogContentText
            component={"section"}
            id="about-dialog-description"
            ref={descriptionElementRef}
            tabIndex={-1}
          >
            <Typography variant="h5">
              Hell Let Loose (HLL) Community RCON (CRCON)
            </Typography>
            <Typography>{t("about.description")}</Typography>
            <Divider sx={{ my: 2 }} />
            <Typography variant="body1">
              {t("about.apiVersion")}:{" "}
              {isLoading ? t("common.loading") : apiVersion}
            </Typography>
            <Typography variant="subtitle2">
              {isUpToDate ? t("about.upToDate") : t("about.updateAvailable")}
            </Typography>
            <Typography variant="subtitle2">
              {t("about.lastChecked")}: {dayjs(lastUpdate).format("LLL")}{" "}
              <IconButton
                variant="text"
                size="small"
                aria-label={t("about.lastChecked")}
                onClick={() => {
                  forceUpdate();
                }}
              >
                <RefreshIcon />
              </IconButton>
            </Typography>

            {open && releases.length > 0 && (
              <>
                <Suspense
                  fallback={<Skeleton variant="rectangular" height={200} />}
                >
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="h6">
                    {t("about.latestRelease")} {releases[0].name}
                  </Typography>
                  <Typography variant="subtitle2" sx={{ mb: 2 }}>
                    {dayjs(releases[0].published_at).format("LLL")}
                  </Typography>
                  <ReleaseNotes release={releases[0]} />
                </Suspense>
              </>
            )}
          </DialogContentText>
        </DialogContent>

        <DialogActions>
          <Button onClick={handleClose}>{t("common.close")}</Button>
        </DialogActions>
      </Dialog>
    </React.Fragment>
  );
}
