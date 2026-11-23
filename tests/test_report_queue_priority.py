"""Worker batch ordering on SQLite and PostgreSQL, with a controlled clock and fake RCON."""
import pytest

from tests.test_leadership_vote import db as sqlite_db
from tests.test_leadership_vote_postgres import postgres
from tests.test_report_admin import setup, service, current, report, transport
from tests.test_report_reason import semantic, complete, decision


@pytest.fixture(params=["sqlite_db", "postgres"])
def db(request):
    return request.getfixturevalue(request.param)


@pytest.mark.parametrize("elapsed", [0, service.MAX_REPORT_AGE])
def test_ready_assessment_gets_a_slot_ahead_of_pending_and_sending(semantic, elapsed):
    db, _, ctx = semantic
    message = "!admin BattlefieldHero never answers us in command chat"
    waiting = [report(semantic, message)["id"] for _ in range(6)]
    for incident in waiting[::2]:
        complete(semantic, incident, None, status="sending")
    first, second = (report(semantic, message)["id"] for _ in range(2))
    complete(semantic, second, decision())
    complete(semantic, first, decision())
    db.clock.now += elapsed
    ctx["captured_at"] = db.clock.now
    with db() as sess:
        tasks = service.pending(sess, 1, limit=4, due_at=db.clock.now)
        assert [task.incident_id for task in tasks] == [first, second, *waiting[:2]]
    api = transport()
    service.tick(api, 1)
    for incident in (first, second):
        assert current(db, incident)["report_admin"]["status"] == "queued"
    for incident in waiting:
        assert current(db, incident)["report_admin"]["status"] == "classifying"
    api.kick.assert_not_called()


@pytest.mark.parametrize("finished", [True, False])
def test_expired_assessment_still_goes_to_manual(semantic, finished):
    db, _, ctx = semantic
    message = "!admin BattlefieldHero never answers us in command chat"
    incident = report(semantic, message)["id"]
    db.clock.now += service.MAX_REPORT_AGE + 1
    ctx["captured_at"] = db.clock.now
    if finished:
        complete(semantic, incident, decision())
    api = transport()
    service.tick(api, 1)
    result = current(db, incident)["report_admin"]
    assert result["status"] == "manual" and "AI interpretation expired" in result["result"]
    api.kick.assert_not_called()
