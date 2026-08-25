import { InputBase, Box, styled, IconButton } from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import CloseIcon from "@mui/icons-material/Close";
import React from "react";
import { useTranslation } from "react-i18next";

const SearchWrapper = styled(Box)({
  display: "flex",
  alignItems: "center",
  justifyContent: "start",
  minHeight: 44,
  minWidth: 0,
  width: "100%",
});

const StyledInput = styled(InputBase)(({theme}) => ({
  flex: 1,
  marginLeft: theme.spacing(1),
  minHeight: 44,
  minWidth: 0,
  "& .MuiInputBase-input": {
    boxSizing: "border-box",
    minHeight: 44,
    paddingBlock: 0,
  },
  "& .MuiButtonBase-root": {
    display: "inline-flex",
    minHeight: 44,
    minWidth: 44,
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
