"""Exercise buildx digest promotion using a disposable loopback OCI registry."""
import hashlib
import json
import os
import subprocess
import unittest
from urllib.request import Request, urlopen

from scripts import promote_release_images as release


def encoded(value):
    payload = json.dumps(value, separators=(",", ":")).encode()
    return payload, "sha256:" + hashlib.sha256(payload).hexdigest()


def seed_image(registry, repo, version):
    base = f"http://{registry}/v2/{repo}"
    manifest_type = "application/vnd.oci.image.manifest.v1+json"
    config_type = "application/vnd.oci.image.config.v1+json"
    index_type = "application/vnd.oci.image.index.v1+json"

    def put_manifest(tag, kind, document):
        data, digest = encoded(document)
        req = Request(f"{base}/manifests/{tag}", method="PUT", data=data, headers={"Content-Type": kind})
        with urlopen(req, timeout=10) as response:
            assert response.headers["Docker-Content-Digest"] == digest
        return {"mediaType": kind, "size": len(data), "digest": digest}

    children = []
    for arch in ("amd64", "arm64"):
        config, digest = encoded({"architecture": arch, "os": "linux", "config": {"Labels": {"version": version, "image": repo}},
                                  "rootfs": {"type": "layers", "diff_ids": []}})
        with urlopen(Request(base + "/blobs/uploads/", data=b"", method="POST"), timeout=10) as response:
            upload = response.headers["Location"]
        if upload.startswith("/"):
            upload = f"http://{registry}{upload}"
        separator = "&" if "?" in upload else "?"
        req = Request(upload + separator + "digest=" + digest, data=config, method="PUT",
                      headers={"Content-Type": "application/octet-stream"})
        with urlopen(req, timeout=10):
            pass
        entry = put_manifest(f"{version}-{arch}", manifest_type, {
            "schemaVersion": 2, "mediaType": manifest_type, "layers": [],
            "config": {"mediaType": config_type, "size": len(config), "digest": digest},
        })
        children.append({**entry, "platform": {"os": "linux", "architecture": arch}})
    return put_manifest(version, index_type, {"schemaVersion": 2, "mediaType": index_type,
                                              "manifests": children})["digest"]


@unittest.skipUnless(os.environ.get("TEST_LOCAL_RELEASE_REGISTRY") == "1", "requires disposable Docker registry")
class RegistryPromotionTests(unittest.TestCase):
    def test_promotes_and_restores_real_manifest_indexes(self):
        from time import sleep
        from unittest.mock import patch

        summary = patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": ""})
        summary.start()
        self.addCleanup(summary.stop)

        container = subprocess.check_output(["docker", "run", "-d", "--rm", "-p", "127.0.0.1::5000", "registry:2"],
                                            text=True).strip()
        self.addCleanup(subprocess.run, ["docker", "rm", "-f", "-v", container], check=True)
        registry = subprocess.check_output(["docker", "port", container, "5000/tcp"], text=True).strip()
        self.assertRegex(registry, r"^127\.0\.0\.1:[0-9]+$")
        for attempt in range(30):
            try:
                with urlopen(f"http://{registry}/v2/", timeout=2):
                    break
            except OSError:
                if attempt == 29:
                    raise
                sleep(0.2)
        old, new = {}, {}
        for repo in ("backend", "frontend"):
            key = f"{registry}/{repo}"
            old[key] = seed_image(registry, repo, "latest")
            new[key] = seed_image(registry, repo, "v1.0.1")
        real_tag = release.tag_latest
        def reject_second(repo, digest):
            if repo.endswith("/frontend") and digest == new[repo]:
                raise RuntimeError("fixture rejects second promotion")
            real_tag(repo, digest)
        with patch.object(release, "tag_latest", side_effect=reject_second):
            with self.assertRaisesRegex(RuntimeError, "fixture rejects"):
                release.promote("v1.0.1", new)
        for repo, digest in old.items():
            self.assertEqual(release.digest_of(f"{repo}:latest"), digest)
        release.promote("v1.0.1", new)
        for repo, digest in new.items():
            self.assertEqual(release.digest_of(f"{repo}:latest"), digest)
            self.assertEqual(release.digest_of(f"{repo}:v1.0.1"), digest)
