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
import { Link as RouterLink } from "react-router-dom";
import { useTranslation } from "react-i18next";

export default function AboutDialog() {
  const { t } = useTranslation();
  const [open, setOpen] = React.useState(false);
  const theme = useTheme();
  const isSmallScreen = useMediaQuery(theme.breakpoints.down("md"));

  const { data: apiVersion, isLoading } = useQuery({
    queryKey: ["apiVersion"],
    queryFn: cmd.GET_VERSION,
    initialData: "0.0.0",
  });

  const handleClickOpen = () => {
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
                  <FontAwesomeIcon icon={faCircleQuestion} />
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
            <Button component={RouterLink} to="/updates" onClick={handleClose} sx={{ mt: 2 }}>{t("updates.title")}</Button>
          </DialogContentText>
        </DialogContent>

        <DialogActions>
          <Button onClick={handleClose}>{t("common.close")}</Button>
        </DialogActions>
      </Dialog>
    </React.Fragment>
  );
}
