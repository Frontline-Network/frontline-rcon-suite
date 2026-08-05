from django.urls import path

from . import mobile, mobile_context, mobile_incidents

MOBILE_API_DOCUMENTATION = [
    {
        "endpoint": "mobile/v1/discovery",
        "allowed_http_methods": ["GET"],
        "permissions_required": [],
        "description": "Discover the versioned CRCON mobile API.",
    },
    {
        "endpoint": "mobile/v1/pairings",
        "allowed_http_methods": ["POST"],
        "permissions_required": ["api.can_manage_own_mobile_devices"],
        "description": "Create a single-use, web-approved mobile pairing.",
    },
    {
        "endpoint": "mobile/v1/pairings/{id}",
        "allowed_http_methods": ["GET"],
        "permissions_required": ["api.can_manage_own_mobile_devices"],
        "description": "Read the web-visible state of a pairing.",
    },
    {
        "endpoint": "mobile/v1/pairings/{id}/scan",
        "allowed_http_methods": ["POST"],
        "permissions_required": [],
        "description": "Consume the QR secret and register a pending phone.",
    },
    {
        "endpoint": "mobile/v1/pairings/{id}/approve",
        "allowed_http_methods": ["POST"],
        "permissions_required": ["api.can_manage_own_mobile_devices"],
        "description": "Approve or deny the comparison code in CRCON.",
    },
    {
        "endpoint": "mobile/v1/pairings/{id}/exchange",
        "allowed_http_methods": ["POST"],
        "permissions_required": [],
        "description": "Exchange an approved one-time pairing for device tokens.",
    },
    {
        "endpoint": "mobile/v1/tokens/refresh",
        "allowed_http_methods": ["POST"],
        "permissions_required": [],
        "description": "Rotate a mobile refresh token and issue a new access token.",
    },
    {
        "endpoint": "mobile/v1/devices",
        "allowed_http_methods": ["GET"],
        "permissions_required": ["api.can_manage_own_mobile_devices"],
        "description": "List own devices or all devices with owner permission.",
    },
    {
        "endpoint": "mobile/v1/devices/{id}",
        "allowed_http_methods": ["PATCH", "DELETE"],
        "permissions_required": ["api.can_manage_own_mobile_devices"],
        "description": "Update or immediately revoke a mobile device.",
    },
    {
        "endpoint": "mobile/v1/bootstrap",
        "allowed_http_methods": ["GET"],
        "permissions_required": [],
        "description": "Load installation, device, server, user, permission metadata, and permitted incident assignees.",
    },
    {
        "endpoint": "mobile/v1/incidents",
        "allowed_http_methods": ["GET", "POST"],
        "permissions_required": ["api.can_view_admin_incidents"],
        "description": "List or manually create admin incidents.",
    },
    {
        "endpoint": "mobile/v1/incidents/{id}",
        "allowed_http_methods": ["GET", "PATCH"],
        "permissions_required": ["api.can_view_admin_incidents"],
        "description": "Read and transition a revision-protected incident.",
    },
    {
        "endpoint": "mobile/v1/incidents/{id}/notes",
        "allowed_http_methods": ["POST"],
        "permissions_required": ["api.can_create_admin_incidents"],
        "description": "Append an immutable private note to an incident.",
    },
    {
        "endpoint": "mobile/v1/incidents/{id}/actions",
        "allowed_http_methods": ["POST"],
        "permissions_required": [],
        "description": "Run a permission-checked, idempotent mobile player, squad removal, or squad disband action.",
    },
    {
        "endpoint": "mobile/v1/incidents/{id}/subjects",
        "allowed_http_methods": ["POST"],
        "permissions_required": ["api.can_create_admin_incidents"],
        "description": "Add a confirmed player or squad subject to an incident.",
    },
    {
        "endpoint": "mobile/v1/incidents/{id}/subjects/{subject_id}",
        "allowed_http_methods": ["PATCH"],
        "permissions_required": ["api.can_create_admin_incidents"],
        "description": "Confirm, reject, or prioritize an incident subject.",
    },
    {
        "endpoint": "mobile/v1/players/search",
        "allowed_http_methods": ["GET"],
        "permissions_required": [],
        "description": "Search permission-filtered historical and online players.",
    },
    {
        "endpoint": "mobile/v1/autobalancer",
        "allowed_http_methods": ["GET"],
        "permissions_required": ["api.can_view_autobalancer"],
        "description": "Load a minimal, read-only Fair Autobalancer live status for one server.",
    },
    {
        "endpoint": "mobile/v1/players/{player_id}",
        "allowed_http_methods": ["GET"],
        "permissions_required": [],
        "description": "Load a permission-filtered player dossier and live context.",
    },
    {
        "endpoint": "mobile/v1/servers/{server_number}/roster",
        "allowed_http_methods": ["GET"],
        "permissions_required": ["api.can_view_team_view"],
        "description": "Load the current team and squad roster.",
    },
    {
        "endpoint": "mobile/v1/servers/{server_number}/squads/{team}/{squad}",
        "allowed_http_methods": ["GET"],
        "permissions_required": ["api.can_view_team_view"],
        "description": "Load one live squad and its members.",
    },
    {
        "endpoint": "ws/mobile/v1/incidents",
        "allowed_http_methods": ["WEBSOCKET"],
        "permissions_required": ["api.can_view_admin_incidents"],
        "description": "Stream incident changes from a reconnectable timestamp cursor.",
    },
]


urlpatterns = [
    path("discovery", mobile.discovery, name="mobile-discovery"),
    path("pairings", mobile.create_pairing, name="mobile-create-pairing"),
    path(
        "pairings/<uuid:pairing_id>",
        mobile.pairing_status,
        name="mobile-pairing-status",
    ),
    path(
        "pairings/<uuid:pairing_id>/scan",
        mobile.scan_pairing,
        name="mobile-scan-pairing",
    ),
    path(
        "pairings/<uuid:pairing_id>/approve",
        mobile.approve_pairing,
        name="mobile-approve-pairing",
    ),
    path(
        "pairings/<uuid:pairing_id>/exchange",
        mobile.exchange_pairing,
        name="mobile-exchange-pairing",
    ),
    path("tokens/refresh", mobile.refresh_token, name="mobile-refresh-token"),
    path("devices", mobile.devices, name="mobile-devices"),
    path("devices/<uuid:device_id>", mobile.device_detail, name="mobile-device-detail"),
    path("bootstrap", mobile.bootstrap, name="mobile-bootstrap"),
    path("incidents", mobile_incidents.incidents, name="mobile-incidents"),
    path(
        "incidents/<uuid:incident_id>",
        mobile_incidents.incident_detail,
        name="mobile-incident-detail",
    ),
    path(
        "incidents/<uuid:incident_id>/notes",
        mobile_incidents.incident_notes,
        name="mobile-incident-notes",
    ),
    path(
        "incidents/<uuid:incident_id>/actions",
        mobile_incidents.incident_actions,
        name="mobile-incident-actions",
    ),
    path(
        "incidents/<uuid:incident_id>/subjects",
        mobile_incidents.incident_subjects,
        name="mobile-incident-subjects",
    ),
    path(
        "incidents/<uuid:incident_id>/subjects/<uuid:subject_id>",
        mobile_incidents.incident_subject_detail,
        name="mobile-incident-subject-detail",
    ),
    path("players/search", mobile_context.players_search, name="mobile-player-search"),
    path(
        "autobalancer",
        mobile_context.autobalancer_status,
        name="mobile-autobalancer-status",
    ),
    path(
        "players/<str:player_id>",
        mobile_context.player_detail,
        name="mobile-player-detail",
    ),
    path(
        "servers/<int:server_number>/roster",
        mobile_context.roster,
        name="mobile-server-roster",
    ),
    path(
        "servers/<int:server_number>/squads/<str:team>/<str:squad>",
        mobile_context.squad_detail,
        name="mobile-squad-detail",
    ),
]
