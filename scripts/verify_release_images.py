"""Pull immutable published images and verify both architecture contents."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def docker(*args):
    return subprocess.check_output(["docker", *args], text=True).strip()


def verify_tags(repository, version, manifest, *, before_promotion=False):
    """An RC must match its own tag, never replace the stable latest image."""
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9][A-Za-z0-9.-]*)?", version):
        raise ValueError("Invalid release version")
    prerelease = "-" in version
    published = json.loads(docker("buildx", "imagetools", "inspect", repository + ":" + version, "--raw"))
    assert published == manifest, f"{repository}:{version} does not match built digest"
    latest = json.loads(docker("buildx", "imagetools", "inspect", repository + ":latest", "--raw"))
    if prerelease:
        assert latest != manifest, "Release candidate unexpectedly replaced stable latest"
    elif not before_promotion:
        assert latest == manifest, f"{repository}:latest does not match built digest"
    return {"prerelease": prerelease, "latest_matches": latest == manifest}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--backend-digest", required=True)
    parser.add_argument("--frontend-digest", required=True)
    parser.add_argument("--require-highlights", action="store_true")
    parser.add_argument("--before-promotion", action="store_true",
                        help="Verify the versioned images while the previous stable pair is still live")
    parser.add_argument("--require-history-version")
    args = parser.parse_args()
    evidence = {"version": args.version, "revision": args.revision, "images": {}}
    expected_image_hash = hashlib.sha256(Path("assets/rcongui/updates/theme-collection.png").read_bytes()).hexdigest()
    for kind, digest, suffix in [("backend", args.backend_digest, ""), ("frontend", args.frontend_digest, "-frontend")]:
        repository = "ghcr.io/frontline-network/frontline-rcon-suite" + suffix
        reference = repository + "@" + digest
        manifest = json.loads(docker("buildx", "imagetools", "inspect", reference, "--raw"))
        tag_checks = verify_tags(repository, args.version, manifest, before_promotion=args.before_promotion)
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
                                "scripts/verify_bundled_release.py", args.version, "--image",
                                *(["--require-highlights"] if args.require_highlights else []))
                checks[platform] = json.loads(result)
                if args.require_history_version:
                    history = docker("run", "--rm", "--platform", platform, "--entrypoint", "python", child,
                                     "scripts/verify_bundled_release.py", args.require_history_version,
                                     "--require-highlights")
                    checks[platform]["inherited_release"] = json.loads(history)
            else:
                result = docker("run", "--rm", "--platform", platform, "--entrypoint", "sh", child, "-ec",
                                'test "$(cat /code/tag_version)" = "$1"; test "$(cat /var/www/tag_version)" = "$1"; '
                                'grep -lF "$1" /var/www/assets/*.js >/dev/null; '
                                'if grep -lE "Mirage:|Pretender intercepted|demo_release_highlights=1" /var/www/assets/*.js; then exit 1; fi; '
                                'sha256sum /var/www/updates/theme-collection.png', "verify", args.version)
                assert result.split()[0] == expected_image_hash, result
                checks[platform] = {"version": args.version, "image_sha256": expected_image_hash, "production_bundle": True}
        evidence["images"][kind] = {"tag": repository + ":" + args.version, "digest": digest, "platforms": platforms, "checks": checks, **tag_checks}
    Path("release-image-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
