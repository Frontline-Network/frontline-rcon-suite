import TranslateRoundedIcon from "@mui/icons-material/TranslateRounded";
import CheckRoundedIcon from "@mui/icons-material/CheckRounded";
import IconButton from "@mui/material/IconButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Tooltip from "@mui/material/Tooltip";
import { useState } from "react";
import { useTranslation } from "react-i18next";

const languages = [
  { code: "de", key: "language.de" },
  { code: "en", key: "language.en" },
];

export default function LanguageSelector({
  touchSafe = false,
  square = false,
}) {
  const { i18n, t } = useTranslation();
  const [anchorEl, setAnchorEl] = useState(null);
  const language = i18n.resolvedLanguage || "de";

  const selectLanguage = async (code) => {
    await i18n.changeLanguage(code);
    document.documentElement.lang = code;
    setAnchorEl(null);
  };

  return (
    <>
      <Tooltip title={t("language.label")}>
        <IconButton
          size="small"
          aria-label={t("language.label")}
          onClick={(event) => setAnchorEl(event.currentTarget)}
          sx={{
            ...(touchSafe ? { minWidth: 45, minHeight: 45 } : {}),
            ...(square ? { borderRadius: "0 !important" } : {}),
          }}
        >
          <TranslateRoundedIcon />
        </IconButton>
      </Tooltip>
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{ horizontal: "right", vertical: "bottom" }}
        transformOrigin={{ horizontal: "right", vertical: "top" }}
      >
        {languages.map(({ code, key }) => (
          <MenuItem
            key={code}
            selected={language === code}
            onClick={() => selectLanguage(code)}
          >
            <ListItemIcon
              sx={{ visibility: language === code ? "visible" : "hidden" }}
            >
              <CheckRoundedIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText>{t(key)}</ListItemText>
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}
