import {
  Box,
  Divider,
  IconButton,
  Stack,
  Select,
  MenuItem,
} from "@mui/material";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import KeyboardArrowLeftIcon from "@mui/icons-material/KeyboardArrowLeft";
import KeyboardDoubleArrowLeftIcon from "@mui/icons-material/KeyboardDoubleArrowLeft";
import KeyboardDoubleArrowRightIcon from "@mui/icons-material/KeyboardDoubleArrowRight";
import { useTranslation } from "react-i18next";

export const TablePagination = ({ table }) => {
  const { t, i18n } = useTranslation();

  return (
  <Stack
    direction={"row"}
    justifyContent={"end"}
    alignItems={"center"}
    gap={0.25}
  >
    <IconButton
      aria-label={t("common.pagination.first")}
      onClick={() => table.firstPage()}
      disabled={!table.getCanPreviousPage()}
      size="small"
      sx={{ borderRadius: 0, p: 0.5 }}
    >
      <KeyboardDoubleArrowLeftIcon />
    </IconButton>
    <IconButton
      aria-label={t("common.pagination.previous")}
      onClick={() => table.previousPage()}
      disabled={!table.getCanPreviousPage()}
      size="small"
      sx={{ borderRadius: 0, p: 0.5 }}
    >
      <KeyboardArrowLeftIcon />
    </IconButton>
    <Box sx={{ textWrap: "nowrap", alignSelf: "center", mx: 0.5 }}>
      {t("common.pagination.page", {
        current: table.getState().pagination.pageIndex + 1,
        total: table.getPageCount().toLocaleString(i18n.resolvedLanguage),
      })}
    </Box>
    <IconButton
      aria-label={t("common.pagination.next")}
      onClick={() => table.nextPage()}
      disabled={!table.getCanNextPage()}
      size="small"
      sx={{ borderRadius: 0, p: 0.5 }}
    >
      <KeyboardArrowRightIcon />
    </IconButton>
    <IconButton
      aria-label={t("common.pagination.last")}
      onClick={() => table.lastPage()}
      disabled={!table.getCanNextPage()}
      size="small"
      sx={{ borderRadius: 0, p: 0.5 }}
    >
      <KeyboardDoubleArrowRightIcon />
    </IconButton>
    <Divider orientation="vertical" flexItem />
    <Box sx={{ mx: 0.25 }}>
      <Select
        value={table.getState().pagination.pageSize}
        onChange={(e) => table.setPageSize(e.target.value)}
        size="small"
        sx={{ borderRadius: 0 }}
        inputProps={{ "aria-label": t("common.pagination.pageSize") }}
      >
        {[50, 100, 150, 250, 500].map((pageSize) => (
          <MenuItem key={pageSize} value={pageSize}>
            {t("common.pagination.show", { count: pageSize })}
          </MenuItem>
        ))}
      </Select>
    </Box>
  </Stack>
  );
};
