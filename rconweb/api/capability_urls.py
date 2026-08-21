from django.urls import path

from .capabilities import capabilities

urlpatterns = [
    path("capabilities", capabilities, name="integration-capabilities"),
]
