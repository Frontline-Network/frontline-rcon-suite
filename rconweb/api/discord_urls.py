from django.urls import path

from . import discord_integration

urlpatterns = [
    path(
        "integration",
        discord_integration.integration_detail,
        name="discord-integration",
    ),
    path(
        "options",
        discord_integration.integration_options,
        name="discord-options",
    ),
    path(
        "pairings",
        discord_integration.create_discord_pairing,
        name="discord-pairing",
    ),
    path("connect", discord_integration.connect_integration, name="discord-connect"),
    path(
        "pairings/complete",
        discord_integration.complete_pairing,
        name="discord-pairing-complete",
    ),
    path(
        "actions/prepare",
        discord_integration.prepare_action,
        name="discord-action-prepare",
    ),
    path(
        "action-templates",
        discord_integration.discord_action_templates,
        name="discord-action-templates",
    ),
    path(
        "incidents/transition",
        discord_integration.transition_incident,
        name="discord-incident-transition",
    ),
    path(
        "actions/<uuid:preparation_id>/execute",
        discord_integration.execute_action,
        name="discord-action-execute",
    ),
    path(
        "moderation-feedback",
        discord_integration.moderation_feedback,
        name="discord-moderation-feedback",
    ),
    path(
        "moderation-results",
        discord_integration.moderation_result,
        name="discord-moderation-result",
    ),
    path("usage", discord_integration.integration_usage, name="discord-usage"),
    path("test-message", discord_integration.test_message, name="discord-test-message"),
]
