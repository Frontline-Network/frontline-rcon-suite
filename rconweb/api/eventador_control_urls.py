from django.urls import path

from . import eventador_control

urlpatterns = [
    path(
        "capabilities",
        eventador_control.capabilities,
        name="eventador-control-capabilities",
    ),
    path("state", eventador_control.state, name="eventador-control-state"),
    path(
        "steps/prepare",
        eventador_control.prepare_step,
        name="eventador-control-prepare",
    ),
    path(
        "steps/<uuid:preparation_id>/execute",
        eventador_control.execute_step,
        name="eventador-control-execute",
    ),
    path(
        "results/<uuid:idempotency_key>",
        eventador_control.result,
        name="eventador-control-result",
    ),
]
