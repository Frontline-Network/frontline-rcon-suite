"""Small, bounded views of case evidence; player chat remains untrusted text."""

import re


def safe(value, limit=160):
    text = " ".join(str(value or "–").split())[:limit]
    text = text.replace("@", "＠").replace("<", "‹").replace(">", "›")
    return re.sub(r"([\\`*_~|])", r"\\\1", text)


def case_fields(report, language):
    reason = report.get("reason_analysis") or {}
    decision = reason.get("decision") or {}
    interpretation = []
    if decision:
        interpretation = [
            {
                "name": (
                    "🤖 KI-Einordnung der Meldung"
                    if language == "de"
                    else "🤖 AI report interpretation"
                ),
                "value": (
                    safe(decision.get("rationale"), 500)
                    + "\n"
                    + safe(decision.get("allegation_excerpt"), 250)
                    + "\n"
                    + safe(", ".join(decision.get("uncertainties") or []), 150)
                )[:1000],
                "inline": False,
            }
        ]
    a = report.get("assessment") or {}
    if not a:
        return interpretation
    de = language == "de"
    lines = []
    if a.get("kind") == "cheat_review":
        title = (
            "🔎 Cheatprüfung – nur Admin-Entscheidung"
            if de
            else "🔎 Cheat review – human decision only"
        )
        lines.append(
            "24 h Tempbann nur nach zusätzlichen Belegen und manueller Freigabe (TB)."
            if de
            else "24-hour temp ban only after additional evidence and manual approval (TB)."
        )
        if a.get("priority") == "high":
            lines.append("⚠ Priorisierte Beobachtung / Prioritized observation")
        for w in a.get("windows", [])[:3]:
            categories = (
                ", ".join(
                    f"{safe(k, 30)}: {v}" for k, v in w.get("categories", {}).items()
                )
                or "–"
            )
            lines.append(
                f"{w.get('seconds', 0) // 60} min ({w.get('observed_seconds', 0)} s): {w.get('kills', 0)} K / {w.get('deaths', 0)} D · {categories}"
            )
        lines.extend(safe(reason, 200) for reason in a.get("reasons", [])[:3])
        if a.get("role_history"):
            lines.append(
                (
                    "Beobachtete Rollenwechsel: "
                    if de
                    else "Observed role history entries: "
                )
                + str(len(a["role_history"]))
            )
    else:
        title = "📋 Teamkill-Einzelfall" if de else "📋 Individual teamkill case"
        lines.extend(
            [
                f"Melder-TK / Reporter TK: {a.get('reporter_teamkills', 0)} · gegenseitig / reciprocal: {a.get('reciprocal_teamkills', 0)}",
                f"Entschuldigungen / Apologies: {len(a.get('apologies', []))} · TK danach / subsequent TK: {a.get('kills_after_apology', 0)}",
                f"Mögliche Explosions-Mehrfachkills / possible explosion multikills: {a.get('possible_explosion_bursts', 0)}",
                (
                    "Anzahl, Wiederholung und Schweigen allein sind kein Absichtsbeweis."
                    if de
                    else "Count, repetition and silence alone do not prove intent."
                ),
            ]
        )
    lines.extend(safe(v, 190) for v in a.get("limitations", [])[:3])
    result = [{"name": title, "value": "\n".join(lines)[:1000] or "–", "inline": False}]
    timeline = a.get("timeline") or []
    if timeline:
        selected = timeline[:3] + timeline[-3:] if len(timeline) > 6 else timeline
        details = []
        for row in selected:
            at = row.get("at")
            stamp = f"<t:{int(at)}:T>" if isinstance(at, (int, float)) else "–"
            label = f"#{row['log_id']} " if row.get("log_id") else "live "
            if str(row.get("type")).startswith("CHAT["):
                body = f"{safe(row.get('name'), 40)}: {safe(row.get('body'), 90)}"
            else:
                body = f"{safe(row.get('type'), 16)} {safe(row.get('name'), 35)} → {safe(row.get('victim_name'), 35)} · {safe(row.get('weapon'), 35)}"
            details.append(f"{stamp} {label}{body}")
        omitted = a.get("timeline_omitted", 0) + max(0, len(timeline) - len(selected))
        if omitted:
            details.append(f"+{omitted} · Vollständige Logs prüfen / Review full logs")
        result.append(
            {
                "name": "Zeitlicher Auszug / Timeline excerpt",
                "value": "\n".join(details)[:1000],
                "inline": False,
            }
        )
    return interpretation + result
