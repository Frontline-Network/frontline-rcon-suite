from pathlib import Path
from unittest import TestCase


ROOT = Path(__file__).parents[1]


class FrontendReleaseContractTests(TestCase):
    def test_version_file_is_served_by_admin_frontend(self):
        dockerfile = (ROOT / "Dockerfile-frontend").read_text()
        nginx = (ROOT / "rcongui" / "nginx.conf").read_text()

        self.assertIn(
            "COPY --from=adminbuild /code/tag_version /var/www/tag_version",
            dockerfile,
        )
        self.assertIn("location = /tag_version", nginx)
        self.assertIn('default_type text/plain;', nginx)
        self.assertIn('Cache-Control "no-store, no-cache, must-revalidate, max-age=0"', nginx)
