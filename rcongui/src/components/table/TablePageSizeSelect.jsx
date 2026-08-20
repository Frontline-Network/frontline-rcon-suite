import { Select, MenuItem } from "@mui/material";
import { useTranslation } from "react-i18next";

export const TablePageSizeSelect = ({
  pageSize,
  setPageSize,
  options = [10, 20, 50, 100],
}) => {
  const { t } = useTranslation();
  return (
    <Select
      value={pageSize}
      inputProps={{ "aria-label": t("common.pagination.pageSize") }}
      onChange={(e) => setPageSize(e.target.value)}
      size="small"
      MenuProps={{
        PaperProps: {
          sx: {
            borderRadius: 0,
          },
        },
      }}
      sx={{
        "& .MuiPaper-root": {
          borderRadius: 0,
        },
        '& .MuiSelect-select': {
          padding: '4px 32px 4px 8px',
          minWidth: '40px',
          backgroundColor: (theme) => theme.palette.background.default,
          borderRadius: 0,
        },
        '& .MuiOutlinedInput-notchedOutline, & .MuiList-root': {
          borderRadius: 0,
        },
      }}
    >
      {options.map((option) => (
        <MenuItem 
          key={option} 
          value={option}
          dense
          sx={{ 
            py: 0.5,
            minHeight: 'auto',
            borderRadius: 0,
          }}
        >
          {option}
        </MenuItem>
      ))}
    </Select>
  );
};
