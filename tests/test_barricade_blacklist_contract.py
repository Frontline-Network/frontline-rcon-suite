import asyncio
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
import django

django.setup()
from api import barricade


def test_missing_blacklist_is_rejected():
    session = Mock()
    session.query.return_value.scalar.return_value = False
    with patch.object(barricade.models, 'enter_session', return_value=nullcontext(session)):
        with pytest.raises(barricade.BarricadeRequestError, match='Blacklist does not exist'):
            barricade.assert_blacklist_exists.func(999)
    session.query.return_value.scalar.assert_called_once_with()


def test_existing_record_is_reused_only_from_requested_active_list():
    records = [SimpleNamespace(id=11, blacklist_id=1), SimpleNamespace(id=22, blacklist_id=2)]
    with patch.object(barricade, 'lock', return_value=nullcontext()), \
         patch.object(barricade.models, 'enter_session', return_value=nullcontext(object())), \
         patch.object(barricade, 'get_player_blacklist_records', return_value=records) as lookup, \
         patch.object(barricade, 'add_record_to_blacklist') as create:
        assert barricade.ban_player.func('synthetic-player', 2, 'reason') == 22
    assert lookup.call_args.kwargs['include_expired'] is False
    assert lookup.call_args.kwargs['include_other_servers'] is True
    create.assert_not_called()


def test_record_on_different_list_does_not_count_as_requested_list():
    records = [SimpleNamespace(id=11, blacklist_id=1)]
    with patch.object(barricade, 'lock', return_value=nullcontext()), \
         patch.object(barricade.models, 'enter_session', return_value=nullcontext(object())), \
         patch.object(barricade, 'get_player_blacklist_records', return_value=records), \
         patch.object(barricade, 'add_record_to_blacklist', return_value={'id': 22}) as create:
        assert barricade.ban_player.func('synthetic-player', 2, 'reason') == 22
    assert create.call_args.kwargs['blacklist_id'] == 2


def test_partial_failure_reports_only_confirmed_ids():
    async def run():
        payload = barricade.BanPlayersRequestPayload.model_validate({
            'player_ids': {'confirmed': None, 'failed': None},
            'config': {'banlist_id': '2', 'reason': 'reason'},
        })
        with patch.object(barricade, 'assert_blacklist_exists', AsyncMock()), \
             patch.object(barricade, 'ban_player', AsyncMock(side_effect=[22, None])):
            with pytest.raises(barricade.BarricadeRequestError) as error:
                await barricade.BarricadeConsumer().ban_players(payload)
        assert error.value.kwargs == {'ban_ids': {'confirmed': '22'}}
    asyncio.run(run())


def test_success_returns_string_record_ids():
    async def run():
        payload = barricade.BanPlayersRequestPayload.model_validate({
            'player_ids': {'confirmed': None}, 'config': {'banlist_id': '2', 'reason': 'reason'},
        })
        with patch.object(barricade, 'assert_blacklist_exists', AsyncMock()), \
             patch.object(barricade, 'ban_player', AsyncMock(return_value=22)):
            assert await barricade.BarricadeConsumer().ban_players(payload) == {'ban_ids': {'confirmed': '22'}}
    asyncio.run(run())


def test_websocket_reply_marks_partial_failure_instead_of_success():
    async def run():
        consumer = barricade.BarricadeConsumer()
        consumer.send_json = AsyncMock()
        request = barricade.RequestBody.model_validate({
            'id': 17, 'request': 'ban_players',
            'payload': {'player_ids': {'confirmed': None, 'failed': None},
                        'config': {'banlist_id': '2', 'reason': 'reason'}},
        })
        with patch.object(barricade, 'assert_blacklist_exists', AsyncMock()), \
             patch.object(barricade, 'ban_player', AsyncMock(side_effect=[22, None])):
            await consumer.handle_request(request)
        response = consumer.send_json.await_args.args[0]
        assert response['id'] == 17 and response['failed'] is True
        assert response['response']['ban_ids'] == {'confirmed': '22'}
        assert 'None' not in response['response']['ban_ids'].values()
    asyncio.run(run())


def test_unban_passes_requested_list_and_reports_actual_result():
    with patch.object(barricade, 'remove_record_from_blacklist', return_value=False) as remove:
        assert barricade.unban_player.func(11, 2) is False
    remove.assert_called_once_with(record_id=11, expected_blacklist_id=2)
    with patch.object(barricade, 'remove_record_from_blacklist', return_value=True):
        assert barricade.unban_player.func(11, 2) is True


def test_unban_rejects_wrong_list_and_reports_partial_result():
    async def run():
        consumer = barricade.BarricadeConsumer()
        payload = barricade.UnbanPlayersRequestPayload.model_validate({
            'ban_ids': ['11', '22'], 'config': {'banlist_id': '2'},
        })
        with patch.object(barricade, 'assert_blacklist_exists', AsyncMock()), \
             patch.object(barricade, 'unban_player', AsyncMock(side_effect=[True, False])) as unban:
            with pytest.raises(barricade.BarricadeRequestError) as error:
                await consumer.unban_players(payload)
        assert error.value.kwargs == {'ban_ids': ['11']}
        assert [call.args for call in unban.await_args_list] == [(11, 2), (22, 2)]
    asyncio.run(run())
