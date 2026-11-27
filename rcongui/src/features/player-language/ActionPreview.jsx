import { useEffect, useState } from "react";
import { Alert, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/hooks/useAuth";
import { allowed, write } from "./api";

export default function ActionPreview({ text, playerId, category }) {
  const { t } = useTranslation();
  const { permissions } = useAuth();
  const permitted = allowed(permissions, "can_view_message_templates");
  const [preview, setPreview] = useState(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    setPreview(null); setFailed(false);
    if (!permitted || !text || !playerId) return;
    const timer = setTimeout(() => {
      write("preview_player_message", { player_id: playerId, text, category }).then(value => {
        if (active) setPreview(value);
      }).catch(() => { if (active) setFailed(true); });
    }, 400);
    return () => { active = false; clearTimeout(timer); };
  }, [text, playerId, category, permitted]);
  if (!permitted) return null;
  if (failed) return <Alert severity="warning">{t("playerLanguages.previewUnavailable")}</Alert>;
  if (!preview) return null;
  return <Alert severity="info" data-testid="action-language-preview">
    <Typography variant="subtitle2">{t("playerLanguages.delivered")}</Typography>
    <Typography variant="caption">{t("playerLanguages.resolved", { language: preview.delivered_language })}</Typography>
    <Typography sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{preview.text}</Typography>
  </Alert>;
}
