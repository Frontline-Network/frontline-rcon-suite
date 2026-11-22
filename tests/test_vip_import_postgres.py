"""Exercise the multipart VIP replacement and its PostgreSQL-backed worker together."""
import json
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import django
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory
from sqlalchemy import select

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rconweb.rconweb.test_settings")
django.setup()
from api import audit_log, auth, vips
from rcon import api_commands, models, vip_import, workers
from rcon.expiring_vips.service import restore_missing_vips
from rcon.rcon import ServerCtl
from rcon.types import GameEnum
from tests.test_vip_restore_race_postgres import database, vip_admin

ALPHA = "0002000000000000000000000000000a"
BRAVO = "0002000000000000000000000000000b"
END = datetime(2050, 10, 3, 8, 30, tzinfo=timezone.utc)


@pytest.fixture
def scenario(database, vip_admin, monkeypatch):
    api, members, _, remove, _ = vip_admin
    api.config = SimpleNamespace(game=GameEnum.HLL_VIETNAM)
    with database.begin() as db:
        models.AuditLog.__table__.create(db.get_bind())
        db.scalar(select(models.PlayerID)).player_id = ALPHA
        db.scalar(select(models.PlayerVIP)).expiration = END
        bravo = models.PlayerID(player_id=BRAVO)
        db.add(bravo)
        db.flush()
        db.add_all(models.PlayerVIP(player_id_id=bravo.id, server_number=n, expiration=END) for n in (3, 4))
    members.clear()
    members.update({ALPHA: "Alpha", BRAVO: "Bravo"})
    enqueue = Mock()
    monkeypatch.setattr(auth, "check_api_key", lambda req: None)
    monkeypatch.setattr(audit_log, "enter_session", database.begin)
    monkeypatch.setattr(vip_import, "enter_session", database.begin)
    monkeypatch.setattr(vips, "rcon_api", api)
    monkeypatch.setattr(vips, "send_to_discord_audit", Mock())
    monkeypatch.setattr(vips, "worker_bulk_vip", enqueue)
    monkeypatch.setattr(api_commands, "get_rcon_api", lambda: api)

    def request(content=None):
        factory = RequestFactory()
        if content is None:
            req = factory.get("/api/download_vips")
        else:
            req = factory.post("/api/upload_vips", {"file": SimpleUploadedFile("vip.txt", content)})
        req.user = SimpleNamespace(username="admin", is_authenticated=True, has_perms=lambda _: True)
        return req

    def submit(content):
        return json.loads(vips.upload_vips(request(content)).content)

    def run_job():
        rows, = enqueue.call_args.args
        return workers.bulk_vip(rows, mode=enqueue.call_args.kwargs["mode"])

    def stored(server=3):
        with database() as db:
            return dict(db.execute(select(models.PlayerID.player_id, models.PlayerVIP.expiration)
                        .join(models.PlayerVIP, models.PlayerVIP.player_id_id == models.PlayerID.id)
                        .where(models.PlayerVIP.server_number == server)).all())
    return SimpleNamespace(api=api, members=members, remove=remove, enqueue=enqueue, submit=submit, request=request,
                           run=run_job, stored=stored, export=lambda: vips.download_vips(request()).content)


def line(pid, name, expiry=END):
    return f"{pid} {name} {expiry.isoformat()}\n".encode()


@pytest.mark.parametrize("bad", [b"truncated", b"bad-id Bravo", b"\xff", b"", b"duplicate",
                                 b"76561198000000001 Steam", line(BRAVO, "Bravo").replace(b"2050-10", b"2050-99")])
def test_invalid_file_never_enqueues_a_partial_replacement(scenario, bad):
    first = line(ALPHA, "Alpha")
    content = first + (first if bad == b"duplicate" else bad) if bad else b""
    response = scenario.submit(content)
    assert response["failed"] and response["error"]
    scenario.enqueue.assert_not_called()
    assert scenario.stored() == {ALPHA: END, BRAVO: END}


@pytest.mark.parametrize("missing", [False, True])
def test_replacement_and_export_include_stored_only_rights(scenario, monkeypatch, missing):
    if missing:
        del scenario.members[BRAVO]
    exported = scenario.export().decode()
    assert BRAVO in exported and END.isoformat() in exported
    add = Mock(side_effect=AssertionError("unchanged VIP must not be regranted"))
    monkeypatch.setattr(ServerCtl, "add_vip", add)
    assert not scenario.submit(line(ALPHA, "Alpha"))["failed"]
    assert scenario.run() == ["ALL OK"]
    assert scenario.stored() == {ALPHA: END}
    assert scenario.stored(4) == {BRAVO: END}
    assert scenario.members == {ALPHA: "Alpha"}
    add.assert_not_called()
    assert restore_missing_vips(scenario.api) == 0
    assert scenario.run() == ["ALL OK"]
    assert scenario.remove.call_count == (0 if missing else 1)


@pytest.mark.parametrize("operation", ["grant", "removal"])
@pytest.mark.parametrize("outcome", ["rejected", "timeout"])
def test_worker_reports_partial_outcomes(scenario, monkeypatch, operation, outcome):
    change = Mock(return_value=False, side_effect=TimeoutError() if outcome == "timeout" else None)
    if operation == "grant":
        monkeypatch.setattr(ServerCtl, "add_vip", change)
        content = line(ALPHA, "Alpha", END + timedelta(days=2))
    else:
        scenario.remove.side_effect = change
        content = line(ALPHA, "Alpha")
    assert not scenario.submit(content)["failed"]
    results = scenario.run()
    assert results and "ALL OK" not in results
    assert any((ALPHA if operation == "grant" else BRAVO) in msg for msg in results)
    change.assert_called_once()
    assert scenario.stored() == {ALPHA: END, BRAVO: END}
    assert set(scenario.members) == {ALPHA, BRAVO}


def test_valid_roundtrip_and_in_place_update(scenario):
    del scenario.members[BRAVO]
    assert not scenario.submit(scenario.export())["failed"]
    assert scenario.run() == ["ALL OK"]
    assert scenario.members == {ALPHA: "Alpha", BRAVO: BRAVO}
    new_end = END + timedelta(days=3)
    assert not scenario.submit(line(ALPHA.upper(), "Alpha One", new_end) + line(BRAVO, BRAVO))["failed"]
    assert scenario.run() == ["ALL OK"]
    assert scenario.members[ALPHA] == "Alpha One"
    assert scenario.stored() == {ALPHA: new_end, BRAVO: END}
    scenario.remove.assert_not_called()


def test_retry_after_lost_removal_reply_checks_both_sources(scenario):
    def applied_with_lost_reply(pid):
        scenario.members.pop(pid)
        raise TimeoutError("reply lost")

    scenario.remove.side_effect = applied_with_lost_reply
    assert not scenario.submit(line(ALPHA, "Alpha"))["failed"]
    assert "ALL OK" not in scenario.run()
    assert BRAVO not in scenario.members and BRAVO in scenario.stored()
    assert scenario.run() == ["ALL OK"]
    scenario.remove.assert_called_once_with(BRAVO)
    assert restore_missing_vips(scenario.api) == 0
    assert scenario.stored(4) == {BRAVO: END}


def test_tracked_jobs_have_independent_status(scenario, monkeypatch):
    get_job = Mock(return_value={"status": "finished", "result": ["ALL OK"]})
    monkeypatch.setattr(vips, "get_job_results", get_job)
    keys = []
    for _ in range(2):
        req = scenario.request(line(ALPHA, "Alpha"))
        req.POST = req.POST.copy()
        req.POST["track_job"] = "1"
        result = json.loads(vips.upload_vips(req).content)["result"]
        status = scenario.request()
        status.GET = {"upload_id": result["upload_id"]}
        vips.upload_vips_result(status)
        key = scenario.enqueue.call_args.kwargs["job_key"]
        get_job.assert_called_with(key)
        keys.append(key)
    assert len(set(keys)) == 2


def test_classic_steam_id_and_legacy_empty_description(scenario):
    scenario.api.config.game = GameEnum.HLL_WW2
    steam = "76561198000000001"
    assert not scenario.submit(f"{steam}  {END.isoformat()}".encode())["failed"]
    assert scenario.enqueue.call_args.args[0] == [(steam, steam, END)]
