from datetime import datetime

from sqlalchemy import create_engine, insert, select

from rcon.models import PlayerID, PlayerSession


def test_session_metadata_accepts_open_and_legacy_incomplete_rows():
    engine = create_engine('sqlite://')
    PlayerID.__table__.create(engine)
    PlayerSession.__table__.create(engine)
    with engine.begin() as connection:
        connection.execute(insert(PlayerID.__table__).values(id=1, steam_id_64='synthetic-player'))
        connection.execute(insert(PlayerSession.__table__), [
            {'id': 1, 'playersteamid_id': 1, 'start': datetime(2026, 1, 1),
             'end': None, 'created': None, 'server_number': 3, 'server_name': 'test'},
            {'id': 2, 'playersteamid_id': 1, 'start': None,
             'end': None, 'created': None, 'server_number': None, 'server_name': None},
        ])
        rows = connection.execute(select(PlayerSession.__table__).order_by(PlayerSession.id)).all()
    assert rows[0].end is None
    assert rows[1].start is rows[1].created is rows[1].server_number is rows[1].server_name is None
