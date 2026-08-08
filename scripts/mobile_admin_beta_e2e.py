"""Run a gated CRCON Mobile Admin beta workflow against one existing incident.

The runner is deliberately read/claim/resolve-only by default.  It never sends
an in-game action unless ``--allow-action`` is supplied together with an
explicit player id, subject id, action, and reason.  It is intended for a
dedicated test player and a private beta environment, not unattended cron use.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class BetaE2EError(RuntimeError):
    """Raised when the remote beta workflow cannot be verified."""


@dataclass
class Client:
    base_url: str
    access_token: str

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        url = f"{self.base_url.rstrip('/')}/api/mobile/v1/{path.lstrip('/')}"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }
        payload = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            payload = json.dumps(body).encode("utf-8")
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        request = Request(url, data=payload, headers=headers, method=method)
        try:
            with urlopen(request, timeout=20) as response:
                raw = response.read().decode("utf-8")
                status = response.status
        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise BetaE2EError(f"{method} {path} returned HTTP {exc.code}: {raw[:400]}") from exc
        except URLError as exc:
            raise BetaE2EError(f"{method} {path} failed: {exc.reason}") from exc
        try:
            envelope = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise BetaE2EError(f"{method} {path} returned non-JSON HTTP {status}") from exc
        if not isinstance(envelope, dict):
            raise BetaE2EError(f"{method} {path} returned an invalid envelope")
        if envelope.get("failed"):
            raise BetaE2EError(f"{method} {path} failed: {envelope.get('error', 'unknown error')}")
        return envelope.get("result")


def _idempotency(prefix: str) -> str:
    return f"beta-e2e-{prefix}-{uuid.uuid4()}"


def _subject_for_player(incident: dict[str, Any], player_id: str) -> dict[str, Any]:
    for subject in incident.get("subjects") or []:
        if (
            subject.get("kind") == "player"
            and subject.get("state") == "confirmed"
            and str(subject.get("player_id") or "") == player_id
        ):
            return subject
        if subject.get("kind") == "squad" and subject.get("state") == "confirmed":
            for member in subject.get("snapshot", {}).get("players", []):
                if str(member.get("player_id") or "") == player_id:
                    return subject
    raise BetaE2EError(
        f"Player {player_id} is not a confirmed subject/member of incident "
        f"{incident.get('id')}"
    )


def run(args: argparse.Namespace) -> None:
    if not args.incident_id:
        raise BetaE2EError("--incident-id is required; create the report in-game first")
    client = Client(args.base_url, args.access_token)

    bootstrap = client.request("GET", "bootstrap")
    if not isinstance(bootstrap, dict):
        raise BetaE2EError("bootstrap did not return an object")
    incident = client.request("GET", f"incidents/{args.incident_id}")
    if not isinstance(incident, dict):
        raise BetaE2EError("incident detail did not return an object")
    if str(incident.get("id")) != args.incident_id:
        raise BetaE2EError("incident id mismatch")
    if args.server_number is not None and int(incident.get("server_number")) != args.server_number:
        raise BetaE2EError("incident is on a different server than --server-number")

    print(f"incident {args.incident_id}: {incident.get('status')} / revision {incident.get('revision')}")
    subjects = incident.get("subjects") or []
    confirmed = [item for item in subjects if item.get("state") == "confirmed"]
    print(f"confirmed subjects: {len(confirmed)}; live context: {bool(incident.get('live_context'))}")

    claimed = client.request(
        "PATCH",
        f"incidents/{args.incident_id}",
        body={"operation": "claim", "revision": incident["revision"]},
        idempotency_key=_idempotency("claim"),
    )
    if not isinstance(claimed, dict) or claimed.get("status") != "claimed":
        raise BetaE2EError("incident could not be claimed")
    print(f"claimed by {claimed.get('assigned_to')}; revision {claimed.get('revision')}")

    current = claimed
    if args.note:
        current = client.request(
            "POST",
            f"incidents/{args.incident_id}/notes",
            body={"revision": current["revision"], "note": args.note},
            idempotency_key=_idempotency("note"),
        )
        print("note added")

    if args.allow_action:
        if not args.player_id or not args.subject_id:
            raise BetaE2EError("--allow-action requires --player-id and --subject-id")
        if not args.reason:
            raise BetaE2EError("--allow-action requires --reason")
        subject = _subject_for_player(current, args.player_id)
        if str(subject.get("id")) != args.subject_id:
            raise BetaE2EError("--subject-id does not match the confirmed player context")
        action: dict[str, Any] = {
            "action": args.action,
            "player_id": args.player_id,
            "subject_id": args.subject_id,
            "reason": args.reason,
            "confirmed": True,
        }
        if args.action == "temp_ban":
            action["duration_hours"] = args.duration_hours
        elif args.action == "message":
            if not args.message:
                raise BetaE2EError("message action requires --message")
            action["message"] = args.message
        elif args.action == "comment":
            action["comment"] = args.reason
        result = client.request(
            "POST",
            f"incidents/{args.incident_id}/actions",
            body=action,
            idempotency_key=_idempotency("action"),
        )
        if isinstance(result, dict) and isinstance(result.get("incident"), dict):
            current = result["incident"]
        print(f"action completed: {args.action}; response={type(result).__name__}")
    else:
        print("action skipped (safe default; pass --allow-action only for a dedicated test player)")

    resolved = client.request(
        "PATCH",
        f"incidents/{args.incident_id}",
        body={
            "operation": "resolved",
            "revision": current["revision"],
            "note": "Beta E2E verification",
        },
        idempotency_key=_idempotency("resolve"),
    )
    if not isinstance(resolved, dict) or resolved.get("status") != "resolved":
        raise BetaE2EError("incident could not be resolved")
    print(f"resolved; revision {resolved.get('revision')}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("CRCON_BASE_URL"), required=not os.getenv("CRCON_BASE_URL"))
    parser.add_argument("--access-token", default=os.getenv("CRCON_ACCESS_TOKEN"), required=not os.getenv("CRCON_ACCESS_TOKEN"), help=argparse.SUPPRESS)
    parser.add_argument("--incident-id", default=os.getenv("CRCON_TEST_INCIDENT_ID"))
    parser.add_argument("--server-number", type=int, default=None)
    parser.add_argument("--note", default="")
    parser.add_argument("--allow-action", action="store_true")
    parser.add_argument("--action", choices=("message", "punish", "kick", "temp_ban", "perma_ban", "comment"), default="message")
    parser.add_argument("--player-id", default=None)
    parser.add_argument("--subject-id", default=None)
    parser.add_argument("--reason", default=None)
    parser.add_argument("--message", default=None)
    parser.add_argument("--duration-hours", type=int, default=2)
    return parser.parse_args()


if __name__ == "__main__":
    try:
        run(parse_args())
    except BetaE2EError as exc:
        print(f"beta-e2e: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
