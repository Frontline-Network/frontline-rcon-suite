"""Pull immutable published images and verify both architecture contents."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def docker(*args):
    return subprocess.check_output(["docker", *args], text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--backend-digest", required=True)
    parser.add_argument("--frontend-digest", required=True)
    args = parser.parse_args()
    evidence = {"version": args.version, "revision": args.revision, "images": {}}
    expected_image_hash = hashlib.sha256(Path("assets/rcongui/updates/theme-collection.png").read_bytes()).hexdigest()
    for kind, digest, suffix in [("backend", args.backend_digest, ""), ("frontend", args.frontend_digest, "-frontend")]:
        repository = "ghcr.io/frontline-network/frontline-rcon-suite" + suffix
        reference = repository + "@" + digest
        manifest = json.loads(docker("buildx", "imagetools", "inspect", reference, "--raw"))
        for tag in (args.version, "latest"):
            assert json.loads(docker("buildx", "imagetools", "inspect", repository + ":" + tag, "--raw")) == manifest, f"{kind}:{tag} does not match built digest"
        platforms = {f'{item["platform"]["os"]}/{item["platform"]["architecture"]}': item["digest"]
                     for item in manifest["manifests"] if item["platform"]["os"] != "unknown"}
        assert set(platforms) == {"linux/amd64", "linux/arm64"}, platforms
        checks = {}
        for platform, child_digest in platforms.items():
            child = repository + "@" + child_digest
            docker("pull", "--platform", platform, child)
            config = json.loads(docker("image", "inspect", child))[0]["Config"]
            assert config["Labels"]["org.opencontainers.image.revision"] == args.revision
            assert config["Labels"]["org.opencontainers.image.version"] == args.version
            assert not any("GITHUB_TOKEN=" in value or "GH_TOKEN=" in value or "CRCON_RELEASES_GITHUB_TOKEN=" in value for value in config["Env"])
            if kind == "backend":
                result = docker("run", "--rm", "--platform", platform, "--entrypoint", "python", child,
                                "scripts/verify_bundled_release.py", args.version, "--require-highlights", "--image")
                checks[platform] = json.loads(result)
            else:
                result = docker("run", "--rm", "--platform", platform, "--entrypoint", "sh", child, "-ec",
                                'test "$(cat /code/tag_version)" = "$1"; test "$(cat /var/www/tag_version)" = "$1"; '
                                'grep -lF "$1" /var/www/assets/*.js >/dev/null; '
                                'if grep -lE "Mirage:|Pretender intercepted|demo_release_highlights=1" /var/www/assets/*.js; then exit 1; fi; '
                                'sha256sum /var/www/updates/theme-collection.png', "verify", args.version)
                assert result.split()[0] == expected_image_hash, result
                checks[platform] = {"version": args.version, "image_sha256": expected_image_hash, "production_bundle": True}
        evidence["images"][kind] = {"tag": repository + ":" + args.version, "digest": digest, "platforms": platforms, "checks": checks, "latest_matches": True}
    Path("release-image-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
