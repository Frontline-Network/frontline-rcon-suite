import os
from unittest import TestCase
from unittest.mock import Mock, patch

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("RCONWEB_TEST_MODE", "1")
os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rconweb.rconweb.test_settings")

import django

django.setup()

try:
    from rconweb.api import auto_settings
except ModuleNotFoundError:
    from api import auto_settings


class AutoSettingsServiceRestartTests(TestCase):
    @patch.object(auto_settings, "restart_shared_service")
    @patch.object(auto_settings, "_uses_shared_runtime", return_value=True)
    def test_shared_runtime_uses_cooperative_restart(
        self, _uses_shared_runtime, restart_shared_service
    ):
        client = Mock()

        self.assertTrue(auto_settings._restart_auto_settings_service(client))

        _uses_shared_runtime.assert_called_once_with(client)
        restart_shared_service.assert_called_once_with("auto_settings")
        client.supervisor.getProcessInfo.assert_not_called()

    @patch.object(auto_settings, "_uses_shared_runtime", return_value=False)
    def test_legacy_running_process_keeps_supervisor_restart(self, _uses_shared_runtime):
        client = Mock()
        client.supervisor.getProcessInfo.return_value = {"state": 20}

        self.assertTrue(auto_settings._restart_auto_settings_service(client))

        _uses_shared_runtime.assert_called_once_with(client)
        client.supervisor.stopProcess.assert_called_once_with("auto_settings")
        client.supervisor.startProcess.assert_called_once_with("auto_settings")

    @patch.object(auto_settings, "_uses_shared_runtime", return_value=False)
    def test_legacy_stopped_process_is_not_started_implicitly(
        self, _uses_shared_runtime
    ):
        client = Mock()
        client.supervisor.getProcessInfo.return_value = {"state": 0}

        self.assertTrue(auto_settings._restart_auto_settings_service(client))

        _uses_shared_runtime.assert_called_once_with(client)
        client.supervisor.stopProcess.assert_not_called()
        client.supervisor.startProcess.assert_not_called()
