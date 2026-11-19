"""Player-facing Discord entry points use signed users and private, scoped replies."""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

os.environ.setdefault("DISCORD_SERVICE_DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault(
    "DISCORD_SERVICE_SECRET", "test-secret-that-is-at-least-32-characters"
)
os.environ.setdefault("DISCORD_SERVICE_DRY_RUN", "true")

from fastapi import BackgroundTasks, HTTPException
from discord_service.app.db import Base, SessionLocal, engine
from discord_service.app.models import Integration
from discord_service.app import player_panel as ui
from discord_service.app.player_models import (
    PlayerDMPreference,
    PlayerPanel,
    PrivateReply,
)
from discord_service.app.publish_player_panel import publish
from discord_service.app.security import digest, encrypt

PANEL = "a" * 32
CASE = "180fb4f9-e414-4da2-b95e-c9e150aebe2d"


@pytest.fixture
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        session.add(
            Integration(
                installation_id="mine",
                crcon_base_url="https://rcon.example",
                guild_id="1",
                channel_id="99",
                event_capability_digest=digest("test-secret", "events"),
                action_capability_ciphertext=encrypt("test-secret"),
            )
        )
        session.add(
            PlayerPanel(
                id=PANEL,
                installation_id="mine",
                server_number=3,
                guild_id="1",
                channel_id="2",
                message_id="3",
            )
        )
        session.commit()
        yield session


def interaction(op, kind=3, **changes):
    event = {
        "type": kind,
        "data": {"custom_id": f"vp:{PANEL}:{op}"},
        "guild_id": "1",
        "channel_id": "2",
        "member": {"user": {"id": "123"}},
        "id": "456",
        "locale": "pl",
        "token": "test-token",
    }
    return {**event, **changes}


def test_public_entry_opens_private_form_in_user_interface_language(database):
    response = ui.handle_interaction(
        database, interaction("report"), BackgroundTasks(), Mock()
    )
    assert response["type"] == 9
    assert response["data"]["title"] == "Zgłoś incydent"
    assert len(response["data"]["components"]) == 2


@pytest.mark.parametrize(
    "changes", [{"guild_id": "99"}, {"channel_id": "99"}, {"member": {}}, {"id": "x"}]
)
def test_wrong_scope_cannot_start_player_operation(database, changes):
    tasks = BackgroundTasks()
    response = ui.handle_interaction(
        database, interaction("list", **changes), tasks, Mock()
    )
    assert response["data"]["flags"] == 64 and response["type"] == 4 and not tasks.tasks


def test_submit_routes_actor_and_server_and_binds_private_status(database, monkeypatch):
    payload = interaction("report", 5)
    payload["data"]["components"] = [
        {"type": 1, "components": [{"custom_id": "target", "value": "Baker SL"}]},
        {
            "type": 1,
            "components": [{"custom_id": "message", "value": "Brak komunikacji"}],
        },
    ]
    post = Mock()
    post.return_value.json.return_value = {
        "result": {
            "incident_id": CASE,
            "content": "Zgłoszenie przyjęte.",
            "actions": [{"operation": "list", "label": "Moje zgłoszenia"}],
        }
    }
    private = Mock()
    monkeypatch.setattr(ui, "private_reply", private)
    tasks = BackgroundTasks()
    response = ui.handle_interaction(database, payload, tasks, post)
    assert response == {"type": 5, "data": {"flags": 64}}
    (task,) = tasks.tasks
    task.func(*task.args, **task.kwargs)
    sent = post.call_args.kwargs["json"]
    assert (
        sent["discord_user_id"],
        sent["server_number"],
        sent["channel_id"],
        sent["operation"],
    ) == ("123", 3, "2", "report")
    assert sent["arguments"] == {"target": "Baker SL", "message": "Brak komunikacji"}
    row = database.get(PrivateReply, (PANEL, "123", CASE))
    assert row is not None and row.encrypted_token != "test-token"
    assert (
        private.call_args.args[1]["components"][0]["components"][0]["label"]
        == "Moje zgłoszenia"
    )


def notification(**kwargs):
    return ui.PlayerNotification(
        **{
            **dict(
                installation_id="mine",
                server_number=3,
                discord_user_id="123",
                incident_id=CASE,
                content="Votre demande a été traitée.",
                send_dm=True,
            ),
            **kwargs,
        }
    )


def test_notification_is_private_scoped_and_claimed_once(database, monkeypatch):
    integration = database.get(Integration, "mine")
    dm, reply = Mock(), Mock()
    monkeypatch.setattr(ui, "private_dm", dm)
    monkeypatch.setattr(ui, "private_reply", reply)
    assert (
        ui.notify_player(database, integration, notification(), "voice:mine:1")[
            "delivery"
        ]
        == "disabled"
    )
    database.add(
        PrivateReply(
            panel_id=PANEL,
            discord_user_id="123",
            incident_id=CASE,
            encrypted_token=encrypt("private"),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
        )
    )
    database.commit()
    assert ui.notify_player(database, integration, notification(), "voice:mine:1")[
        "ephemeral_updated"
    ]
    assert not dm.called
    assert (
        ui.notify_player(database, integration, notification(), "voice:mine:1")[
            "delivery"
        ]
        == "already_claimed"
    )
    assert reply.call_count == 1
    database.add(
        PlayerDMPreference(
            installation_id="mine",
            discord_user_id="123",
            enabled=True,
            interaction_id="456",
        )
    )
    database.commit()
    assert ui.notify_player(database, integration, notification(), "voice:mine:2")[
        "dm_sent"
    ]
    assert (
        dm.call_args.args[1]["components"][0]["components"][0]["url"]
        == "https://discord.com/channels/1/2/3"
    )
    assert (
        ui.notify_player(
            database, integration, notification(discord_user_id="124"), "voice:mine:3"
        )["delivery"]
        == "disabled"
    )
    with pytest.raises(HTTPException):
        ui.notify_player(
            database, integration, notification(server_number=4), "voice:mine:1"
        )


def test_publishing_reuses_post_and_validates_channel(database):
    client = Mock()
    client.settings.dry_run = False
    client.upsert.return_value = "3"
    assert publish(database, "mine", 3, "1", "2", client) == "3"
    assert client.upsert.call_args.args[-1] == "3"
    with pytest.raises(ValueError):
        publish(database, "mine", 3, "1", "5", client)
    with pytest.raises(ValueError):
        publish(database, "mine", 3, "6", "2", client)


def test_prefs_apply_latest_consent_and_list_controls(database, monkeypatch):
    edited, post = Mock(), Mock()
    monkeypatch.setattr(ui, "private_reply", edited)
    post.return_value.json.return_value = {"result": {"content": "Enregistré."}}
    for interaction_id, enabled in (("500", True), ("502", False), ("501", True)):
        ui.finish_interaction(
            PANEL,
            "123",
            interaction_id,
            "private",
            "fr",
            "dm",
            {"enabled": enabled},
            post,
        )
    assert database.get(PlayerDMPreference, ("mine", "123")).enabled is False
    ui.finish_interaction(PANEL, "123", "503", "private", "fr", "list", {}, post)
    controls = edited.call_args.args[1]["components"][0]["components"]
    assert {b["custom_id"].split(":")[-1] for b in controls} == {
        "link",
        "language",
        "dm_on",
    }
    assert controls[-1]["label"] == "Activer les messages privés"


def test_signed_player_route_and_capability_boundary(database, monkeypatch):
    import json
    import time
    from nacl.signing import SigningKey
    from fastapi.testclient import TestClient
    from discord_service.app import main

    signing_key = SigningKey.generate()
    monkeypatch.setattr(
        main.get_settings(), "discord_public_key", signing_key.verify_key.encode().hex()
    )
    post = Mock()
    post.return_value.json.return_value = {"result": {"content": "Język zapisany."}}
    monkeypatch.setattr(main, "_crcon_post", post)
    monkeypatch.setattr(ui, "private_reply", Mock())
    payload = interaction("language", 5)
    payload["data"]["components"] = [
        {"type": 1, "components": [{"custom_id": "language_value", "value": "pl"}]}
    ]
    data = json.dumps(payload).encode()
    stamp = str(int(time.time()))
    signature = signing_key.sign(stamp.encode() + data).signature.hex()
    with TestClient(main.app) as client:
        url = "/v1/discord/interactions"
        assert client.post(url, content=data).status_code == 401
        response = client.post(
            url,
            content=data,
            headers={
                "X-Signature-Timestamp": stamp,
                "X-Signature-Ed25519": signature,
                "Content-Type": "application/json",
            },
        )
        assert response.json() == {"type": 5, "data": {"flags": 64}}
        assert post.call_args.kwargs["json"]["arguments"] == {"language": "pl"}
        assert post.call_args.kwargs["json"]["operation"] == "language"
        body = notification().model_dump()
        assert (
            client.post(
                "/v1/player-notifications",
                json=body,
                headers={"Idempotency-Key": "voice:mine:1"},
            ).status_code
            == 404
        )
        assert (
            client.post(
                "/v1/player-notifications",
                json=body,
                headers={
                    "Idempotency-Key": "voice:mine:1",
                    "Authorization": "Bearer test-secret",
                },
            ).json()["delivery"]
            == "disabled"
        )


def test_transient_webhook_retries_even_after_dm_while_stale_and_expired_edits_stop(
    database, monkeypatch
):
    integration = database.get(Integration, "mine")
    database.add_all(
        [
            PrivateReply(
                panel_id=PANEL,
                discord_user_id="123",
                incident_id=CASE,
                encrypted_token=encrypt("test-token"),
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=3),
            ),
            PlayerDMPreference(
                installation_id="mine",
                discord_user_id="123",
                enabled=True,
                interaction_id="600",
            ),
        ]
    )
    database.commit()
    reply, dm = Mock(), Mock()
    reply.side_effect = [
        ui.PrivateReplyError(429),
        None,
        TimeoutError(),
        None,
        ui.PrivateReplyError(404),
    ]
    monkeypatch.setattr(ui, "private_reply", reply)
    monkeypatch.setattr(ui, "private_dm", dm)
    first = ui.notify_player(database, integration, notification(), "voice:mine:10")
    assert first["retry_ephemeral"] and first["dm_sent"] and dm.call_count == 1
    retry = ui.notify_player(database, integration, notification(), "voice:mine:10")
    assert (
        not retry["retry_ephemeral"]
        and retry["ephemeral_updated"]
        and dm.call_count == 1
    )
    assert ui.notify_player(
        database, integration, notification(send_dm=False), "voice:mine:12"
    )["retry_ephemeral"]
    assert ui.notify_player(
        database, integration, notification(send_dm=False), "voice:mine:13"
    )["ephemeral_updated"]
    assert (
        ui.notify_player(
            database, integration, notification(send_dm=False), "voice:mine:12"
        )["delivery"]
        == "already_claimed"
    )
    gone = ui.notify_player(
        database, integration, notification(send_dm=False), "voice:mine:14"
    )
    assert (
        not gone["retry_ephemeral"]
        and gone["delivery"] == "disabled"
        and reply.call_count == 5
    )
    assert database.get(PrivateReply, (PANEL, "123", CASE)) is None


def test_mixed_version_player_route_is_paired_per_panel_and_can_be_cleared(
    database, monkeypatch
):
    from discord_service.app import main, player_callback
    from discord_service.app.player_models import PlayerPanelCallback

    settings = main.get_settings()
    monkeypatch.setattr(settings, "allowed_crcon_hosts", "rcon3.example,rcon4.example")
    monkeypatch.setattr(settings, "discord_application_id", "111")
    binding = database.get(Integration, "mine")
    binding.crcon_base_url = "https://rcon4.example"
    database.add(
        PlayerPanel(
            id="b" * 32,
            installation_id="mine",
            server_number=4,
            guild_id="1",
            channel_id="55",
            message_id="56",
        )
    )
    database.commit()
    discord = Mock()
    discord.settings.dry_run = False
    discord.upsert.return_value = "3"
    check = Mock()
    ping = Mock()
    ping.json.return_value = {"result": {"installation_id": "mine"}}
    listing = Mock()
    listing.json.return_value = {"result": {"content": "No cases"}}
    check.side_effect = [ping, listing]
    monkeypatch.setattr(main, "_crcon_post", check)
    assert (
        publish(
            database,
            "mine",
            3,
            "1",
            "2",
            discord,
            callback_origin="https://rcon3.example",
        )
        == "3"
    )
    assert [c.args[0] for c in check.call_args_list] == [
        "https://rcon3.example/api/discord/v1/diagnostics/ping",
        "https://rcon3.example/api/discord/v1/player-reports",
    ]
    assert all(not c.kwargs["follow_redirects"] for c in check.call_args_list)
    assert check.call_args.kwargs["json"]["operation"] == "list"
    assert check.call_args.kwargs["json"]["guild_id"] == "1"
    assert check.call_args.kwargs["json"]["server_number"] == 3
    root = database.get(PlayerPanel, PANEL)
    other = database.get(PlayerPanel, "b" * 32)
    assert (
        player_callback.effective_origin(database, root, binding)
        == "https://rcon3.example"
    )
    assert (
        player_callback.effective_origin(database, other, binding)
        == "https://rcon4.example"
    )
    assert binding.crcon_base_url == "https://rcon4.example"
    # Another active pairing cannot use this stored capability routing decision.
    wrong = Mock(installation_id="other", guild_id="2")
    with pytest.raises(ValueError):
        player_callback.effective_origin(database, root, wrong)
    relay = Mock()
    relay.return_value.json.return_value = {"result": {"content": "No reports."}}
    monkeypatch.setattr(ui, "private_reply", Mock())
    ui.finish_interaction(PANEL, "123", "789", "token", "en", "list", {}, relay)
    assert (
        relay.call_args.args[0] == "https://rcon3.example/api/discord/v1/player-reports"
    )
    assert relay.call_args.kwargs["follow_redirects"] is False
    with monkeypatch.context() as m:
        m.setattr(settings, "allowed_crcon_hosts", "rcon4.example")
        with pytest.raises(ValueError):
            player_callback.effective_origin(database, root, binding)
    publish(database, "mine", 3, "1", "2", discord, use_installation_callback=True)
    assert database.get(PlayerPanelCallback, PANEL) is None
    assert (
        player_callback.effective_origin(database, root, binding)
        == "https://rcon4.example"
    )


@pytest.mark.parametrize(
    "origin",
    [
        "http://rcon3.example",
        "https://other.example",
        "https://rcon3.example/abc",
        "https://user@rcon3.example",
        "https://rcon3.example:444",
        "https://rcon3.example/#x",
    ],
)
def test_override_rejects_untrusted_origin_before_any_relay(
    database, monkeypatch, origin
):
    from discord_service.app import main

    monkeypatch.setattr(main.get_settings(), "allowed_crcon_hosts", "rcon3.example")
    post = Mock()
    monkeypatch.setattr(main, "_crcon_post", post)
    discord = Mock()
    discord.settings.dry_run = False
    with pytest.raises(ValueError):
        publish(database, "mine", 3, "1", "2", discord, callback_origin=origin)
    assert not post.called and not discord.upsert.called


def test_override_rejects_other_installation_before_publication(database, monkeypatch):
    from discord_service.app import main
    from discord_service.app.player_models import PlayerPanelCallback

    monkeypatch.setattr(main.get_settings(), "allowed_crcon_hosts", "rcon3.example")
    post = Mock()
    post.return_value.json.return_value = {"result": {"installation_id": "different"}}
    monkeypatch.setattr(main, "_crcon_post", post)
    discord = Mock()
    discord.settings.dry_run = False
    with pytest.raises(ValueError):
        publish(
            database,
            "mine",
            3,
            "1",
            "2",
            discord,
            callback_origin="https://rcon3.example",
        )
    assert (
        not discord.upsert.called and database.get(PlayerPanelCallback, PANEL) is None
    )
