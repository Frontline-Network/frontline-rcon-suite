from datetime import datetime, timedelta, timezone
from rcon.models import PlayerID, PlayerSession


def test_ambiguous_legacy_duration_does_not_reduce_verified_playtime(monkeypatch):
    monkeypatch.setenv("SERVER_NUMBER", "3")
    player = PlayerID()
    player.sessions = [
        PlayerSession(server_number=3, start_event_us=1_000_000, end_event_us=601_000_000),
        PlayerSession(server_number=3, start=datetime(2024, 10, 27, 2, 50),
                      end=datetime(2024, 10, 27, 2, 10)),
    ]
    assert player.get_total_playtime_seconds() == 600

def test_get_current_playtime_seconds(monkeypatch):
    monkeypatch.setenv('SERVER_NUMBER', '1')
    now = datetime.now()

    # Create mock sessions
    active_session = PlayerSession(start=now - timedelta(minutes=30), end=None, server_number=1)
    ended_session = PlayerSession(start=now - timedelta(hours=2), end=now - timedelta(hours=1), server_number=1)

    # Create a PlayerID object with mock sessions
    player = PlayerID()

    # Test with an active session (no end defined)
    player.sessions = [active_session]
    playtime = player.get_current_playtime_seconds()
    print(f"Playtime for active session: {playtime} seconds")
    assert playtime > 0, "Playtime should be greater than 0 for active sessions"

    # Test with an ended session (end is defined)
    player.sessions = [ended_session]
    playtime = player.get_current_playtime_seconds()
    print(f"Playtime for ended session: {playtime} seconds")
    assert playtime == 0, "Playtime should be 0 for ended sessions"


def test_late_older_session_does_not_hide_current_or_total_playtime(monkeypatch):
    monkeypatch.setenv('SERVER_NUMBER', '1')
    now = datetime.now(timezone.utc)
    old = now - timedelta(hours=1)
    recent = now - timedelta(minutes=5)
    player = PlayerID()
    player.sessions = [
        PlayerSession(start=old.replace(tzinfo=None), end=(old + timedelta(minutes=10)).replace(tzinfo=None),
                      start_event_us=int(old.timestamp() * 1_000_000),
                      end_event_us=int((old + timedelta(minutes=10)).timestamp() * 1_000_000),
                      created=now.replace(tzinfo=None), server_number=1),
        PlayerSession(start=recent.replace(tzinfo=None), end=None,
                      start_event_us=int(recent.timestamp() * 1_000_000),
                      created=(now - timedelta(minutes=4)).replace(tzinfo=None), server_number=1),
    ]
    assert 295 <= player.get_current_playtime_seconds() <= 310
    assert 895 <= player.get_total_playtime_seconds() <= 910


def test_current_playtime_uses_local_server_session(monkeypatch):
    monkeypatch.setenv('SERVER_NUMBER', '1')
    now = datetime.now(timezone.utc)
    player = PlayerID()
    local = now - timedelta(minutes=5)
    other = now - timedelta(minutes=2)
    player.sessions = [
        PlayerSession(start=other.replace(tzinfo=None), end=now.replace(tzinfo=None),
                      start_event_us=int(other.timestamp() * 1_000_000),
                      created=other.replace(tzinfo=None), server_number=2),
        PlayerSession(start=local.replace(tzinfo=None), end=None,
                      start_event_us=int(local.timestamp() * 1_000_000),
                      created=local.replace(tzinfo=None), server_number=1),
    ]
    assert 295 <= player.get_current_playtime_seconds() <= 310


def test_remote_or_unidentified_session_is_not_treated_as_local(monkeypatch):
    monkeypatch.setenv('SERVER_NUMBER', '1')
    now = datetime.now(timezone.utc)
    player = PlayerID()
    player.sessions = [
        PlayerSession(start=now.replace(tzinfo=None), end=None,
                      start_event_us=int(now.timestamp() * 1_000_000), server_number=2),
        PlayerSession(start=now.replace(tzinfo=None), end=None, server_number=None),
    ]
    assert player.get_current_playtime_seconds() == 0


def test_legacy_start_with_absolute_disconnect_does_not_accumulate_active_time(monkeypatch):
    monkeypatch.setenv('SERVER_NUMBER', '1')
    now = datetime.now(timezone.utc)
    player = PlayerID()
    player.sessions = [PlayerSession(start=(now - timedelta(hours=1)).replace(tzinfo=None), end=None,
        start_event_us=None, end_event_us=int((now - timedelta(minutes=30)).timestamp() * 1_000_000), server_number=1)]
    assert player.get_current_playtime_seconds() == 0
    assert player.get_total_playtime_seconds() == 0
