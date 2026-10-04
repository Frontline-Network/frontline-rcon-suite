import { useEffect, useState } from "react";
import { Box, IconButton, Link, Tooltip, Typography } from "@mui/material";
import { visuallyHidden } from "@mui/utils";
import ContentCopyOutlinedIcon from "@mui/icons-material/ContentCopyOutlined";
import CheckIcon from "@mui/icons-material/Check";
import OpenInNewRoundedIcon from "@mui/icons-material/OpenInNewRounded";
import { useTranslation } from "react-i18next";
import { getPlayerIdentity } from "@/utils/player-identity.mjs";

// Narrow panels can wrap EOS at its midpoint without adding clipboard characters.
function IdentifierValue({ value }) {
  if (!/^[a-f0-9]{32}$/i.test(value)) return value;
  return (
    <>
      {value.slice(0, 16)}
      <wbr />
      {value.slice(16)}
    </>
  );
}

function Identifier({ identifier, profileHint, namedLink, compact }) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  const canCopy =
    typeof navigator !== "undefined" &&
    typeof navigator.clipboard?.writeText === "function";
  const label = t(`playerIdentity.${identifier.kind}`);
  const copyLabel = `${t("common.copy")} ${label}`;
  useEffect(() => {
    if (!copied) return undefined;
    const timer = setTimeout(() => setCopied(false), 2000);
    return () => clearTimeout(timer);
  }, [copied]);
  const copy = async (event) => {
    event.stopPropagation();
    try {
      await navigator.clipboard.writeText(identifier.value);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };
  return (
    <Box
      data-identity-kind={identifier.kind}
      sx={{
        display: "grid",
        gridTemplateColumns: "minmax(0, 1fr) auto",
        alignItems: "center",
        columnGap: 1,
        minWidth: 0,
        px: compact ? 0 : 1.5,
        py: compact ? 0.25 : 1,
        bgcolor: compact ? "transparent" : "action.hover",
        "& + &": {
          borderTop: "1px solid",
          borderColor: compact ? "transparent" : "divider",
        },
      }}
    >
      <Box sx={{ minWidth: 0 }}>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 0.75,
            mb: 0.4,
          }}
        >
          <Typography
            component="span"
            sx={{
              color: "text.secondary",
              fontSize: "0.6875rem",
              lineHeight: 1.4,
              letterSpacing: "0.04em",
              fontWeight: 600,
            }}
          >
            {label}
          </Typography>
          {namedLink && identifier.href ? (
            <Tooltip title={profileHint}>
              <Typography
                component="span"
                sx={{
                  color: "text.secondary",
                  fontSize: "0.625rem",
                  letterSpacing: 0,
                  lineHeight: 1.4,
                  borderLeft: "1px solid",
                  borderColor: "divider",
                  pl: 0.75,
                }}
              >
                {t("playerIdentity.nameLinkShort")}
              </Typography>
            </Tooltip>
          ) : null}
        </Box>
        <Box
          sx={{
            minWidth: 0,
            overflowWrap: "anywhere",
            whiteSpace: "normal",
            fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace",
            fontSize: "0.8125rem",
            lineHeight: 1.6,
            letterSpacing: 0,
            fontWeight: 500,
            color: "text.primary",
          }}
        >
          {identifier.href ? (
            <Tooltip title={profileHint}>
              <Link
                href={identifier.href}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(event) => event.stopPropagation()}
                aria-label={`${label}: ${identifier.value}. ${profileHint}`}
                underline="hover"
                sx={{
                  color: "inherit",
                  font: "inherit",
                  letterSpacing: "inherit",
                  "&:hover": { color: "primary.main" },
                  "&:focus-visible": {
                    outline: "2px solid",
                    outlineColor: "primary.main",
                    outlineOffset: 3,
                  },
                }}
              >
                <IdentifierValue value={identifier.value} />
                <OpenInNewRoundedIcon
                  aria-hidden="true"
                  sx={{
                    fontSize: "0.8rem",
                    ml: 0.6,
                    verticalAlign: "-0.12em",
                    color: "text.secondary",
                  }}
                />
              </Link>
            </Tooltip>
          ) : (
            <IdentifierValue value={identifier.value} />
          )}
        </Box>
      </Box>
      <Tooltip title={copied ? t("common.copied") : copyLabel}>
        <span>
          <IconButton
            className="player-id-copy"
            size="small"
            disabled={!canCopy}
            aria-label={copyLabel}
            onClick={copy}
            sx={{
              width: { xs: 44, md: 32 },
              height: { xs: 44, md: 32 },
              color: copied ? "success.main" : "text.secondary",
              border: "1px solid",
              borderColor: copied ? "success.main" : "divider",
              borderRadius: 0.5,
              "&:focus-visible": {
                outline: "2px solid",
                outlineColor: "primary.main",
                outlineOffset: 2,
              },
            }}
          >
            {copied ? (
              <CheckIcon sx={{ fontSize: "1rem" }} />
            ) : (
              <ContentCopyOutlinedIcon sx={{ fontSize: "0.95rem" }} />
            )}
          </IconButton>
          <Box component="span" role="status" sx={visuallyHidden}>
            {copied ? `${label}: ${t("common.copied")}` : ""}
          </Box>
        </span>
      </Tooltip>
    </Box>
  );
}

export default function PlayerIdentifiers({
  player,
  platform,
  variant = "panel",
}) {
  const { t } = useTranslation();
  const compact = variant === "compact";
  const identity = getPlayerIdentity(
    platform ? { ...player, platform } : player
  );
  const profileHint = identity.profileByName
    ? t("playerIdentity.profileByName", { name: identity.profileName })
    : t("playerIdentity.openProfile");
  if (!identity.identifiers.length) return null;
  return (
    <Box
      data-testid="player-identifiers"
      data-variant={variant}
      sx={{
        minWidth: 0,
        width: "100%",
        maxWidth: "100%",
        containerType: "inline-size",
        containerName: "player-identifiers",
      }}
    >
      <Box
        sx={{
          display: "grid",
          minWidth: 0,
          border: compact ? 0 : "1px solid",
          borderColor: "divider",
          ...(compact
            ? {}
            : {
                "@container player-identifiers (min-width: 680px)": {
                  gridTemplateColumns: `repeat(${identity.identifiers.length}, minmax(0, 1fr))`,
                  "& > [data-identity-kind] + [data-identity-kind]": {
                    borderTop: 0,
                    borderLeft: "1px solid",
                    borderColor: "divider",
                  },
                },
              }),
        }}
      >
        {identity.identifiers.map((identifier) => (
          <Identifier
            key={identifier.kind}
            identifier={identifier}
            profileHint={profileHint}
            namedLink={identity.profileByName}
            compact={compact}
          />
        ))}
      </Box>
    </Box>
  );
}
