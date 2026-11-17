"""Review endpoints are server-scoped and require explicit permissions."""
import json
from unittest import mock

from sqlalchemy import select

from rcon import barricade_scan_journal as journal
from tests.test_barricade_scan_journal_postgres import database, prepare
from tests.test_blacklist_sync_api_postgres import invoke


def test_review_permissions_server_isolation_and_operator_audit(database, monkeypatch):
    prepare(database, monkeypatch)
    monkeypatch.setattr('rcon.api_commands.get_server_number', lambda: '3')
    for server in (3, 4):
        with journal.delivery_scope(server, 'integration-a'):
            item = journal.reserve(server, 'integration-a', 77, 'synthetic-eos', 'HLLV')
            assert journal.finish(item, server, 'integration-a', confirmed=False)
            if server == 3:
                local_id = item
    assert invoke('get_barricade_scan_reviews', 'GET', set()).status_code == 403
    response = invoke('get_barricade_scan_reviews', 'GET', {'api.can_view_blacklists'})
    result = json.loads(response.content)['result']
    assert result['total'] == 1 and result['results'][0]['id'] == local_id
    body = {'delivery_id': local_id, 'integration_id': 'integration-a', 'decision': 'retry',
            'reason': 'synthetic peer confirmed no scan'}
    assert invoke('resolve_barricade_scan_review', 'POST', set(), body).status_code == 403
    with mock.patch('rcon.barricade_scan_dispatch.dispatch') as dispatch:
        response = invoke('resolve_barricade_scan_review', 'POST', {'api.can_change_blacklists'}, body)
    assert response.status_code == 200 and json.loads(response.content)['result'] is True
    dispatch.assert_not_called()
    with database() as session:
        assert session.get(journal.BarricadeScanDelivery, local_id).status == 'queued'
        audit = session.scalar(select(journal.BarricadeScanReviewAudit))
        assert audit.actor == 'Operator' and audit.reason == body['reason']
        assert session.scalars(select(journal.BarricadeScanDelivery).where(
            journal.BarricadeScanDelivery.server_number == 4)).one().status == 'review'
