"""rconweb URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

import os

from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path

from api.browse_logsdir import list_logs


def healthz(_request):
    """Confirm that Django is ready without touching Redis, Postgres, or RCON."""
    return HttpResponse(status=204)

if not os.getenv("HLL_MAINTENANCE_CONTAINER") and not os.getenv(
    "HLL_WH_SERVICE_CONTAINER"
):
    urlpatterns = [
        path("healthz", healthz, name="healthz"),
        path("admin/", admin.site.urls),
        path("accounts/", include("django.contrib.auth.urls")),
        path("api/", include("api.urls")),
        path("api/v1/", include("api.capability_urls")),
        path("api/live-map/v1/", include("api.live_map")),
        path("api/mobile/v1/", include("api.mobile_urls")),
        path("api/discord/v1/", include("api.discord_urls")),
        path("api/eventador/v1/", include("api.eventador_control_urls")),
        path("api/logs/", list_logs),
        path("api/logs/<path:path>", list_logs),
    ]
else:
    urlpatterns = []
