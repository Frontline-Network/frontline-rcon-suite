"""Keep per-instance recovery origins intact across generated deployments."""
from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class ComposeLoader(yaml.SafeLoader):
    pass


ComposeLoader.add_constructor(
    "!reset", lambda loader, node: loader.construct_sequence(node)
)


def load(filename):
    return yaml.load((ROOT / filename).read_text(encoding="utf-8"), Loader=ComposeLoader)


class PasswordRecoveryComposeTests(unittest.TestCase):
    def assert_instance(self, document, number):
        for kind in ("backend", "supervisor"):
            env = document["services"][f"{kind}_{number}"]["environment"]
            self.assertEqual(
                env["CRCON_PUBLIC_URL"],
                "${CRCON_PUBLIC_URL_" + str(number) + ":-${CRCON_PUBLIC_URL:-}}",
            )
            self.assertEqual(
                env["CRCON_PASSWORD_RESET_ENABLED"],
                "${CRCON_PASSWORD_RESET_ENABLED_" + str(number)
                + ":-${CRCON_PASSWORD_RESET_ENABLED:-false}}",
            )
            self.assertEqual(env["EMAIL_HOST_PASSWORD"], "${EMAIL_HOST_PASSWORD:-}")
            self.assertEqual(env["EMAIL_USE_TLS"], "${EMAIL_USE_TLS:-true}")
            self.assertEqual(env["EMAIL_USE_SSL"], "${EMAIL_USE_SSL:-false}")

    def test_single_server_supports_override_and_legacy_global_fallback(self):
        self.assert_instance(load("docker-templates/one-server.yaml"), 1)

    def test_all_generated_instances_have_their_own_origin(self):
        document = load("docker-templates/ten-servers.yaml")
        for number in range(1, 11):
            with self.subTest(number=number):
                self.assert_instance(document, number)

    def test_production_override_preserves_per_instance_settings(self):
        document = load("compose.mobile-admin.yaml")
        for number in range(1, 5):
            with self.subTest(number=number):
                self.assert_instance(document, number)

    def test_shared_workers_do_not_inherit_instance_activation(self):
        document = load("compose.mobile-admin.yaml")
        for name in ("maintenance", "webhook_service", "mobile_push_worker", "discord_report_worker"):
            with self.subTest(service=name):
                env = document["services"][name]["environment"]
                self.assertEqual(env["CRCON_PASSWORD_RESET_ENABLED"], "${CRCON_PASSWORD_RESET_ENABLED:-false}")
                self.assertEqual(env["CRCON_PUBLIC_URL"], "${CRCON_PUBLIC_URL:-}")

    def test_default_installation_contains_no_smtp_credentials(self):
        lines = (ROOT / "default.env").read_text(encoding="utf-8").splitlines()
        self.assertIn("CRCON_PASSWORD_RESET_ENABLED=false", lines)
        self.assertIn("EMAIL_HOST_PASSWORD=", lines)
        self.assertIn("CRCON_PUBLIC_URL=", lines)


if __name__ == "__main__":
    unittest.main()
