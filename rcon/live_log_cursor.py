"""Bounded live-history pages anchored to events, never shifting list offsets."""

import hashlib
import re

from rcon.game_logs import get_recent_logs
from rcon.logs.loop import LogLoop


def event_cursor(line: dict) -> str:
    # This is the log recorder's duplicate identity. Metadata enrichment must
    # not change it; equal timestamps with different messages remain distinct.
    identity = f"{line['timestamp_ms']}|{line['line_without_time']}"
    return hashlib.sha256(identity.encode()).hexdigest()


def get_live_log_page(
    *, limit=500, after=None, before=None, log_history=None, **filters
):
    if after and before:
        raise ValueError("Use either after or before")
    for cursor in (after, before):
        if cursor is not None and not re.fullmatch(r"[0-9a-f]{64}", cursor):
            raise ValueError("Invalid live-log cursor")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 2000:
        raise ValueError("Live-log page size must be between 1 and 2000")

    history = log_history if log_history is not None else LogLoop.get_log_history_list()
    source = (
        history.iter_range(start=0, stop=100_000, page_size=500)
        if callable(getattr(history, "iter_range", None))
        else iter(history[:100_000])
    )
    page, head, seen = [], [], set()
    found = not (after or before)
    reset = None
    has_older = False
    for line in source:
        if not isinstance(line, dict):
            continue
        token = event_cursor(line)
        # Concurrent prepends can overlap Redis pages; never duplicate an event.
        if token in seen:
            continue
        seen.add(token)
        if len(head) < limit + 1:
            head.append(line)
        if before and not found:
            if token == before:
                found = True
            continue
        if after and token == after:
            found = True
            break
        page.append(line)
        if len(page) > limit:
            has_older = True
            if after:
                reset = "window_exceeded"
            break
    if (after or before) and not found:
        reset = reset or "cursor_expired"
        page = head
        has_older = len(head) > limit
    page = page[:limit]
    result = get_recent_logs(log_history=page, end=len(page), **filters)
    result["logs"] = [
        {**line, "cursor_id": event_cursor(line)} for line in result["logs"]
    ]
    result.update(
        newest=event_cursor(page[0]) if page else (after if not reset else None),
        oldest=event_cursor(page[-1]) if page else None,
        has_older=has_older,
        reset=reset,
    )
    return result
