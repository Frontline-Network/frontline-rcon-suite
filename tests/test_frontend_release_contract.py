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

    def test_frontends_keep_compression_across_the_managed_proxy_hop(self):
        nginx = (ROOT / "rcongui" / "nginx.conf").read_text()

        # The host nginx proxy uses its default HTTP/1.0 upstream protocol.
        # Both the admin and public frontend servers must therefore explicitly
        # permit gzip on that trusted hop or JS/CSS/JSON reaches users inflated.
        self.assertEqual(nginx.count("gzip_http_version 1.0;"), 2)
        self.assertEqual(nginx.count("gzip_proxied any;"), 2)
        self.assertEqual(nginx.count("gzip_vary on;"), 2)

        gzip_type_lines = [
            line.strip()
            for line in nginx.splitlines()
            if line.strip().startswith("gzip_types ")
        ]
        self.assertEqual(len(gzip_type_lines), 2)
        self.assertTrue(all("text/html" not in line for line in gzip_type_lines))
