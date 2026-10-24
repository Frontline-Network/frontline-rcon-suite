"""One-off guarded rollback of latest; immutable release tags are never changed."""
import json
import subprocess

TARGETS = {
    "frontline-rcon-suite": (
        "sha256:a061fc2ff0812790cf6bbb167a83adefe1ded4d046ae3bc13595da0094c03fcb",
        "sha256:1110098dcda9bcd16602310bb37e498510118b1acc593ad47d63a8b9e5d6ecf9",
    ),
    "frontline-rcon-suite-frontend": (
        "sha256:ee8b65e7fca16142a74e40f791fdf71ebb74ddacc81bcc69bc13446a60dbabee",
        "sha256:b87b0d88ca906475d3af5df9e2505c8a30508f6ef5a900f2f6855f62789090fa",
    ),
}


def inspect(reference):
    return json.loads(subprocess.check_output([
        "docker", "buildx", "imagetools", "inspect", reference, "--raw",
    ], text=True))


def restore(repository, stable_digest, candidate_digest):
    stable = inspect(repository + "@" + stable_digest)
    candidate = inspect(repository + "@" + candidate_digest)
    assert stable != candidate
    assert inspect(repository + ":v0.9.2") == stable, "Stable tag differs from recorded v0.9.2"
    latest = inspect(repository + ":latest")
    assert latest in (stable, candidate), "Unrelated latest update: refuse to overwrite"
    if latest != stable:
        subprocess.check_call([
            "docker", "buildx", "imagetools", "create", "--tag", repository + ":latest",
            repository + "@" + stable_digest,
        ])
    assert inspect(repository + ":latest") == stable
    assert inspect(repository + ":v0.9.3-rc.1") == candidate
    print(json.dumps({"repository": repository, "latest_restored": stable_digest,
                      "candidate_unchanged": candidate_digest}), flush=True)


if __name__ == "__main__":
    for name, digests in TARGETS.items():
        restore("ghcr.io/frontline-network/" + name, *digests)
