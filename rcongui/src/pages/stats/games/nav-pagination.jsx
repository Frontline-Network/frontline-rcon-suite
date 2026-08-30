import { Button, Stack, Typography } from "@mui/material";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import KeyboardArrowLeftIcon from "@mui/icons-material/KeyboardArrowLeft";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

const createPageWindow = (page, maxPages) => {
  if (maxPages <= 5) {
    return Array.from({ length: maxPages }, (_, index) => index + 1);
  }

  return [...new Set([1, page - 1, page, page + 1, maxPages])]
    .filter((value) => value >= 1 && value <= maxPages)
    .sort((left, right) => left - right);
};

export default function NavPagination({
  page,
  maxPages,
  disabled,
  compact = false,
  ...props
}) {
  const { t } = useTranslation();
  const search = useLocation().search;
  const pages = createPageWindow(page, maxPages);

  const goToPage = (targetPage) => {
    const params = new URLSearchParams(search);
    params.set(
      "page",
      String(Math.min(Math.max(targetPage, 1), Math.max(maxPages, 1)))
    );
    return `?${params.toString()}`;
  };

  if (maxPages <= 0) return null;

  return (
    <Stack
      component="nav"
      aria-label={t("stats.games.pagination")}
      direction="row"
      alignItems="center"
      gap={0.5}
      {...props}
    >
      <Button
        component={Link}
        to={goToPage(page - 1)}
        disabled={disabled || page <= 1}
        aria-label={t("common.pagination.previous")}
        startIcon={<KeyboardArrowLeftIcon />}
        sx={{ minWidth: compact ? 44 : 92, minHeight: 40, borderRadius: 0 }}
      >
        {compact ? null : t("common.pagination.previous")}
      </Button>

      {compact ? (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ minWidth: 78, textAlign: "center", whiteSpace: "nowrap" }}
        >
          {t("stats.games.pageIndicator", { page, maxPages })}
        </Typography>
      ) : (
        pages.map((pageNumber, index) => {
          const previousPage = pages[index - 1];
          const showGap = previousPage && pageNumber - previousPage > 1;

          return (
            <Stack
              key={pageNumber}
              direction="row"
              alignItems="center"
              gap={0.5}
            >
              {showGap && (
                <Typography
                  aria-hidden="true"
                  color="text.secondary"
                  sx={{ px: 0.5 }}
                >
                  …
                </Typography>
              )}
              <Button
                component={Link}
                to={goToPage(pageNumber)}
                disabled={disabled}
                aria-current={page === pageNumber ? "page" : undefined}
                aria-label={t("stats.games.goToPage", { page: pageNumber })}
                variant={page === pageNumber ? "contained" : "outlined"}
                sx={{
                  minWidth: 40,
                  width: 40,
                  minHeight: 40,
                  p: 0,
                  borderRadius: 0,
                }}
              >
                {pageNumber}
              </Button>
            </Stack>
          );
        })
      )}

      <Button
        component={Link}
        to={goToPage(page + 1)}
        disabled={disabled || page >= maxPages}
        aria-label={t("common.pagination.next")}
        endIcon={<KeyboardArrowRightIcon />}
        sx={{ minWidth: compact ? 44 : 92, minHeight: 40, borderRadius: 0 }}
      >
        {compact ? null : t("common.pagination.next")}
      </Button>
    </Stack>
  );
}
