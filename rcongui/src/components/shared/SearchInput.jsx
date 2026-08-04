import { InputBase, Box, styled, IconButton } from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import CloseIcon from "@mui/icons-material/Close";
import React from "react";
import { useTranslation } from "react-i18next";

const SearchWrapper = styled(Box)({
  display: "flex",
  alignItems: "center",
  justifyContent: "start",
  minWidth: 260,
});

const StyledInput = styled(InputBase)(({theme}) => ({
  marginLeft: theme.spacing(1),
  "& .MuiButtonBase-root": {
    display: "none",
  },
  "&:hover .MuiButtonBase-root": {
    display: "inline-flex",
  }
}))

export const SearchInput = React.forwardRef(({ ...props }, ref) => {
  const { t } = useTranslation();
  const { sx, onClear, ...rest } = props;
  return (
    <SearchWrapper sx={sx}>
      <Box sx={{ p: "10px", display: "grid", alignItems: "center" }}>
        <SearchIcon />
      </Box>
      <StyledInput
        inputRef={ref}
        placeholder={props.placeholder ?? t("common.search")}
        inputProps={{
          "aria-label": props.placeholder?.toLowerCase() ?? t("common.search"),
        }}
        endAdornment={onClear ? <IconButton onClick={onClear} aria-label={t("common.clearSelection")} size="small"><CloseIcon /></IconButton> : null}
        {...rest}
      />
    </SearchWrapper>
  );
});

SearchInput.displayName = 'SearchInput';
