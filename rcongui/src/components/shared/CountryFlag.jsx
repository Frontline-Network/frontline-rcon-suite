import { Box } from "@mui/material";
import { getName } from "country-list";

const toFlagEmoji = (country) => {
  const code = String(country ?? "").trim().toUpperCase();
  if (!/^[A-Z]{2}$/.test(code)) return "🏳️";
  return String.fromCodePoint(
    ...[...code].map((character) => 0x1f1a5 + character.charCodeAt(0))
  );
};

export const CountryFlag = ({ country, ...props }) => {
  const countryName = getName(country) ?? country ?? "Unknown";
  return (
    <Box
      component="span"
      role="img"
      aria-label={`Flag of ${countryName}`}
      title={countryName}
      sx={{
        display: "inline-flex",
        width: 20,
        minWidth: 20,
        height: 14,
        alignItems: "center",
        justifyContent: "center",
        fontSize: 14,
        lineHeight: 1,
      }}
      {...props}
    >
      {toFlagEmoji(country)}
    </Box>
  );
};
