import { useEffect, useState } from "react";
import {
  Box,
  IconButton,
  Link,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import ContentCopyOutlinedIcon from "@mui/icons-material/ContentCopyOutlined";
import CheckIcon from "@mui/icons-material/Check";
import { useTranslation } from "react-i18next";
import { getPlayerIdentity } from "@/utils/player-identity.mjs";

function Identifier({ identifier, profileHint }) {
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
    <Stack
      direction="row"
      alignItems="center"
      gap={0.5}
      sx={{
        minWidth: 0,
        display: "grid",
        gridTemplateColumns: {
          xs: "minmax(0, 1fr) auto",
          sm: "auto minmax(0, 1fr) auto",
        },
      }}
      data-identity-kind={identifier.kind}
    >
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ gridColumn: { xs: "1 / -1", sm: "auto" } }}
      >
        {label}:
      </Typography>
      <Box
        sx={{
          minWidth: 0,
          overflowWrap: "anywhere",
          whiteSpace: "normal",
          fontFamily: "monospace",
          fontSize: "0.75rem",
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
            >
              {identifier.value}
            </Link>
          </Tooltip>
        ) : (
          identifier.value
        )}
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
              width: { xs: 44, md: 28 },
              height: { xs: 44, md: 28 },
              flexShrink: 0,
            }}
          >
            {copied ? (
              <CheckIcon color="success" sx={{ fontSize: "0.9rem" }} />
            ) : (
              <ContentCopyOutlinedIcon sx={{ fontSize: "0.9rem" }} />
            )}
          </IconButton>
        </span>
      </Tooltip>
    </Stack>
  );
}

export default function PlayerIdentifiers({ player, platform }) {
  const { t } = useTranslation();
  const identity = getPlayerIdentity(
    platform ? { ...player, platform } : player
  );
  const profileHint = identity.profileByName
    ? t("playerIdentity.profileByName", { name: identity.profileName })
    : t("playerIdentity.openProfile");
  return (
    <Stack
      data-testid="player-identifiers"
      spacing={0.1}
      sx={{ minWidth: 0, maxWidth: "100%" }}
    >
      {identity.identifiers.map((identifier) => (
        <Identifier
          key={identifier.kind}
          identifier={identifier}
          profileHint={profileHint}
        />
      ))}
      {identity.profileByName && identity.platformId ? (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ fontSize: "0.65rem", whiteSpace: "normal" }}
        >
          {t("playerIdentity.nameLinkHint")}
        </Typography>
      ) : null}
    </Stack>
  );
}
