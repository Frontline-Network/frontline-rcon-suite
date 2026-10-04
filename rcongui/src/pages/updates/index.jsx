import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Button,
  Chip,
  LinearProgress,
  List,
  ListItemButton,
  ListItemText,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import DoneAllIcon from "@mui/icons-material/DoneAll";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import PageHeader from "@/components/shared/PageHeader";
import SectionSurface from "@/components/shared/SectionSurface";
import { useUpdateChannel } from "@/hooks/useUpdateChannel";
import { useHighlightUI } from "@/features/updates/highlight-state";
import NewReleasesOutlinedIcon from "@mui/icons-material/NewReleasesOutlined";

// Release text comes from a private repository. No raw HTML, external images,
// embedded resources, or repository links are activated in the RCON reader.
function ReleaseText({ text }) {
  const { t } = useTranslation();
  return (
    <Box
      sx={{
        lineHeight: 1.8,
        overflowWrap: "anywhere",
        "& h2, & h3, & h4": {
          fontSize: "1.1rem",
          lineHeight: 1.4,
          mt: 3,
          mb: 1.5,
        },
        "& p, & li": { color: "text.secondary" },
        "& strong": { color: "text.primary" },
        "& ul, & ol": { pl: 2.5 },
        "& pre": {
          p: 2,
          bgcolor: "action.hover",
          overflowX: "auto",
          fontSize: ".8rem",
        },
        "& code": { fontSize: ".85em" },
        "& table": { borderCollapse: "collapse", width: "100%" },
        "& td, & th": {
          textAlign: "left",
          p: 1,
          borderBottom: 1,
          borderColor: "divider",
        },
      }}
    >
      <ReactMarkdown
        skipHtml
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <Typography component="h3" variant="h6" sx={{ mb: 2 }}>
              {children}
            </Typography>
          ),
          h2: ({ children }) => <h3>{children}</h3>,
          a: ({ children }) => <span>{children}</span>,
          img: ({ alt }) =>
            alt ? (
              <Typography component="span" color="text.secondary">
                {alt}
              </Typography>
            ) : null,
          table: ({ children }) => (
            <Box sx={{ overflowX: "auto" }}>
              <table>{children}</table>
            </Box>
          ),
        }}
      >
        {text || t("updates.noNotes")}
      </ReactMarkdown>
    </Box>
  );
}

export default function Updates() {
  const { t, i18n } = useTranslation();
  const channel = useUpdateChannel();
  const openHighlights = useHighlightUI((state) => state.requestOpen);
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState("");
  const words = search.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  const entries = channel.releases.filter((entry) =>
    words.every((word) =>
      `${entry.name} ${entry.tag_name} ${entry.body}`
        .toLocaleLowerCase()
        .includes(word)
    )
  );
  const requested = params.get("release");
  const selected =
    entries.find((entry) => entry.tag_name === requested) || entries[0];
  const choose = (tag) => {
    setParams({ release: tag }, { preventScrollReset: true });
    document.getElementById("main-content")?.scrollTo({ top: 0 });
  };
  const date = (value) => {
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime())
      ? "—"
      : parsed.toLocaleDateString(i18n.resolvedLanguage, { dateStyle: "long" });
  };
  const status = channel.isError
    ? "unavailable"
    : channel.data?.status || "unverified";
  return (
    <Box sx={{ minWidth: 0 }}>
      <PageHeader
        title={t("updates.title")}
        subtitle={t("updates.subtitle")}
        actions={
          <Stack direction="row" gap={1} flexWrap="wrap">
            {channel.highlightRelease && channel.data?.highlight_state && <Button variant="outlined" startIcon={<NewReleasesOutlinedIcon />} onClick={openHighlights}>{t("releaseHighlights.title")}</Button>}
            <Button
              startIcon={<DoneAllIcon />}
              onClick={channel.markAsRead}
              disabled={!channel.unreadCount}
            >
              {t("updates.markRead")}
            </Button>
            <Button
              startIcon={<RefreshIcon />}
              onClick={() => channel.forceUpdate()}
              disabled={channel.isFetching}
            >
              {t("updates.refresh")}
            </Button>
          </Stack>
        }
      />
      <Stack gap={2.5}>
        {channel.data?.preview && (
          <Alert severity="info">{t("updates.preview")}</Alert>
        )}
        <SectionSurface sx={{ p: { xs: 2, md: 3 } }}>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            gap={2}
            alignItems={{ sm: "center" }}
            justifyContent="space-between"
          >
            <Box>
              <Typography variant="overline" color="text.secondary">
                {t("updates.installed")}
              </Typography>
              <Stack direction="row" alignItems="center" gap={1}>
                {status === "ready" && (
                  <CheckCircleOutlineIcon color="success" />
                )}
                <Typography variant="h5" component="p">
                  {channel.data?.installed_version || "—"}
                </Typography>
                {channel.unreadCount > 0 && (
                  <Chip
                    label={t("updates.unread")}
                    size="small"
                    color="primary"
                  />
                )}
              </Stack>
            </Box>
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ maxWidth: 540 }}
            >
              {t("updates.scope")}
            </Typography>
          </Stack>
        </SectionSurface>
        {channel.isFetching && (
          <LinearProgress aria-label={t("updates.loading")} />
        )}
        {!channel.isPending && status !== "ready" && (
          <Alert severity={status === "unavailable" ? "warning" : "info"}>
            {t(`updates.status.${status}`, {
              defaultValue: t("updates.status.unavailable"),
            })}
            {status === "version_mismatch" && (
              <Typography variant="body2" sx={{ mt: 1 }}>
                {t("updates.versions", {
                  frontend: channel.data?.frontend_version,
                  backend: channel.data?.installed_version,
                })}
              </Typography>
            )}
          </Alert>
        )}
        {channel.data?.stale && status === "ready" && (
          <Alert severity="warning">{t("updates.stale")}</Alert>
        )}
        {channel.releases.length > 0 && (
          <>
            <TextField
              fullWidth
              label={t("updates.search")}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            {requested &&
              !channel.releases.some(
                (entry) => entry.tag_name === requested
              ) && <Alert severity="info">{t("updates.notAvailable")}</Alert>}
            {selected ? (
              <SectionSurface
                sx={{
                  display: "grid",
                  gridTemplateColumns: {
                    xs: "minmax(0, 1fr)",
                    md: "300px minmax(0, 1fr)",
                  },
                  alignItems: "start",
                }}
              >
                <Box
                  sx={{
                    minWidth: 0,
                    borderRight: { md: 1 },
                    borderBottom: { xs: 1, md: 0 },
                    borderColor: { xs: "divider", md: "divider" },
                  }}
                >
                  <Typography
                    variant="overline"
                    component="h2"
                    color="text.secondary"
                    sx={{ px: 2.5, pt: 2 }}
                  >
                    {t("updates.history")}
                  </Typography>
                  <List
                    component="nav"
                    aria-label={t("updates.history")}
                    sx={{
                      display: { xs: "none", md: "block" },
                      maxHeight: "65vh",
                      overflowY: "auto",
                    }}
                  >
                    {entries.map((entry) => (
                      <ListItemButton
                        key={entry.tag_name}
                        selected={selected.tag_name === entry.tag_name}
                        aria-current={
                          selected.tag_name === entry.tag_name
                            ? "page"
                            : undefined
                        }
                        onClick={() => choose(entry.tag_name)}
                        sx={{ px: 2.5, py: 1.5, borderRadius: "0 !important" }}
                      >
                        <ListItemText
                          primary={entry.tag_name}
                          secondary={`${
                            entry.current ? t("updates.current") + " · " : ""
                          }${date(entry.published_at)}`}
                          primaryTypographyProps={{ fontWeight: 650 }}
                        />
                      </ListItemButton>
                    ))}
                  </List>
                  <Box sx={{ display: { xs: "block", md: "none" }, p: 2 }}>
                    <TextField
                      select
                      fullWidth
                      label={t("updates.version")}
                      value={selected.tag_name}
                      onChange={(event) => choose(event.target.value)}
                    >
                      {entries.map((entry) => (
                        <MenuItem key={entry.tag_name} value={entry.tag_name}>
                          {entry.tag_name}
                          {entry.current ? ` · ${t("updates.current")}` : ""}
                        </MenuItem>
                      ))}
                    </TextField>
                  </Box>
                </Box>
                <Box
                  component="article"
                  aria-labelledby="release-heading"
                  sx={{ minWidth: 0, p: { xs: 2, md: 4 } }}
                >
                  <Stack
                    direction="row"
                    gap={1}
                    flexWrap="wrap"
                    sx={{ mb: 1.5 }}
                  >
                    <Chip size="small" label={selected.tag_name} />
                    {selected.current && (
                      <Chip
                        size="small"
                        color="success"
                        variant="outlined"
                        label={t("updates.current")}
                      />
                    )}
                    {selected.prerelease && (
                      <Chip
                        size="small"
                        color="warning"
                        label={t("updates.prerelease")}
                      />
                    )}
                  </Stack>
                  <Typography
                    id="release-heading"
                    component="h2"
                    variant="h5"
                    sx={{ overflowWrap: "anywhere" }}
                  >
                    {selected.name}
                  </Typography>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mt: 1, mb: 3 }}
                  >
                    {t("updates.published", {
                      date: date(selected.published_at),
                    })}
                  </Typography>
                  <ReleaseText text={selected.body} />
                </Box>
              </SectionSurface>
            ) : (
              <Alert
                severity="info"
                action={
                  <Button onClick={() => setSearch("")}>
                    {t("updates.clear")}
                  </Button>
                }
              >
                {t("updates.noResults")}
              </Alert>
            )}
          </>
        )}
      </Stack>
    </Box>
  );
}
