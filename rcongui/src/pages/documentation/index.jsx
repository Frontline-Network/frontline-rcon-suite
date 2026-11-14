import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Button,
  List,
  ListItemButton,
  ListItemText,
  MenuItem,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";
import CodeOutlinedIcon from "@mui/icons-material/CodeOutlined";
import PageHeader from "@/components/shared/PageHeader";
import SectionSurface from "@/components/shared/SectionSurface";
import DocumentationText from "./DocumentationText";
import ApiReference from "./ApiReference";
import { helpArticles } from "./content";
import { frenchHelp } from "./content-fr";

export default function Documentation() {
  const { t, i18n } = useTranslation();
  const code = (i18n.resolvedLanguage || "en").split("-")[0];
  const language = ["de", "en", "fr"].includes(code) ? code : "en";
  const localizedArticles = helpArticles.map((entry) => ({
    ...entry,
    title: { ...entry.title, fr: frenchHelp[entry.id]?.title || entry.title.en },
    summary: { ...entry.summary, fr: frenchHelp[entry.id]?.summary || entry.summary.en },
    body: { ...entry.body, fr: frenchHelp[entry.id]?.body || entry.body.en },
  }));
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState("");
  const activeTab = params.get("tab") === "api" ? "api" : "help";
  const words = search.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  const articles = localizedArticles.filter((article) =>
    words.every((word) =>
      [
        article.title[language],
        article.summary[language],
        article.body[language],
      ]
        .join(" ")
        .toLocaleLowerCase()
        .includes(word)
    )
  );
  const requested = params.get("topic");
  useEffect(() => {
    setSearch("");
    document.getElementById("main-content")?.scrollTo({ top: 0 });
  }, [requested, activeTab]);
  const article = articles.find((item) => item.id === requested) || articles[0];
  const selectTopic = (topic) => {
    setParams({ topic }, { preventScrollReset: true });
    document.getElementById("main-content")?.scrollTo({ top: 0 });
  };
  return (
    <Box sx={{ minWidth: 0 }}>
      <PageHeader
        title={t("documentation.title")}
        subtitle={t("documentation.subtitle")}
      />
      <Tabs
        value={activeTab}
        onChange={(_event, value) =>
          setParams(value === "api" ? { tab: "api" } : {})
        }
        aria-label={t("documentation.sections")}
        sx={{ mb: 3, borderBottom: 1, borderColor: "divider" }}
      >
        <Tab
          id="documentation-tab-help"
          aria-controls="documentation-panel-help"
          value="help"
          label={t("documentation.help")}
          icon={<MenuBookOutlinedIcon />}
          iconPosition="start"
        />
        <Tab
          id="documentation-tab-api"
          aria-controls="documentation-panel-api"
          value="api"
          label={t("documentation.api")}
          icon={<CodeOutlinedIcon />}
          iconPosition="start"
        />
      </Tabs>
      <Box
        role="tabpanel"
        id={`documentation-panel-${activeTab}`}
        aria-labelledby={`documentation-tab-${activeTab}`}
      >
        {activeTab === "api" ? (
          <ApiReference language={language} />
        ) : (
          <Stack gap={2}>
            <TextField
              label={t("documentation.searchHelp")}
              fullWidth
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            {requested &&
              !helpArticles.some((item) => item.id === requested) && (
                <Alert severity="info">{t("documentation.topicMissing")}</Alert>
              )}
            {article ? (
              <SectionSurface
                sx={{
                  display: "grid",
                  gridTemplateColumns: {
                    xs: "minmax(0, 1fr)",
                    md: "260px minmax(0, 1fr)",
                  },
                  alignItems: "start",
                }}
              >
                <Box
                  sx={{
                    borderRight: { md: 1 },
                    borderBottom: { xs: 1, md: 0 },
                    borderColor: { xs: "divider", md: "divider" },
                    minWidth: 0,
                  }}
                >
                  <List
                    component="nav"
                    aria-label={t("documentation.topics")}
                    sx={{ display: { xs: "none", md: "block" }, py: 1 }}
                  >
                    {articles.map((item) => (
                      <ListItemButton
                        key={item.id}
                        selected={item.id === article.id}
                        aria-current={
                          item.id === article.id ? "page" : undefined
                        }
                        onClick={() => selectTopic(item.id)}
                        sx={{ px: 2.5, py: 1, borderRadius: "0 !important" }}
                      >
                        <ListItemText
                          primary={item.title[language]}
                          secondary={item.summary[language]}
                          primaryTypographyProps={{
                            fontSize: "0.875rem",
                            fontWeight: 600,
                          }}
                          secondaryTypographyProps={{
                            sx: {
                              mt: 0.5,
                              fontSize: "0.75rem",
                              lineHeight: 1.6,
                            },
                          }}
                        />
                      </ListItemButton>
                    ))}
                  </List>
                  <Box sx={{ display: { xs: "block", md: "none" }, p: 2 }}>
                    <TextField
                      select
                      fullWidth
                      label={t("documentation.topics")}
                      value={article.id}
                      onChange={(event) => selectTopic(event.target.value)}
                    >
                      {articles.map((item) => (
                        <MenuItem key={item.id} value={item.id}>
                          {item.title[language]}
                        </MenuItem>
                      ))}
                    </TextField>
                  </Box>
                </Box>
                <Box
                  component="article"
                  aria-labelledby="documentation-article-title"
                  sx={{ p: { xs: 2, md: 3, xl: 4 }, minWidth: 0 }}
                >
                  <Typography
                    component="h2"
                    variant="h5"
                    id="documentation-article-title"
                    sx={{ mb: 1 }}
                  >
                    {article.title[language]}
                  </Typography>
                  <Typography
                    color="text.secondary"
                    sx={{
                      mb: 3,
                      pb: 3,
                      borderBottom: 1,
                      borderColor: "divider",
                    }}
                  >
                    {article.summary[language]}
                  </Typography>
                  <DocumentationText>
                    {article.body[language]}
                  </DocumentationText>
                </Box>
              </SectionSurface>
            ) : (
              <SectionSurface sx={{ p: 3 }}>
                <Typography role="status">
                  {t("documentation.noResults")}
                </Typography>
                <Button onClick={() => setSearch("")} sx={{ mt: 1 }}>
                  {t("documentation.clear")}
                </Button>
              </SectionSurface>
            )}
          </Stack>
        )}
      </Box>
    </Box>
  );
}
