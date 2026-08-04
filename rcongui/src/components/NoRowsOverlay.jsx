import InboxOutlinedIcon from "@mui/icons-material/InboxOutlined";
import { Box } from "@mui/material";
import { styled } from "@mui/material/styles";
import { useTranslation } from "react-i18next";

const StyledGridOverlay = styled("div")(({ theme }) => ({
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  minHeight: 180,
  color: theme.palette.text.secondary,
}));

export function NoRowsOverlay() {
  const { t } = useTranslation();

  return (
    <StyledGridOverlay>
      <InboxOutlinedIcon
        aria-hidden
        sx={{ flexShrink: 0, fontSize: 64, color: "text.disabled" }}
      />
      <Box sx={{ mt: 1 }}>{t("common.noData")}</Box>
    </StyledGridOverlay>
  );
}
