"""Move latest to two verified manifest digests. Called under the shared stable-channel lock."""
import argparse
import os
import re
import subprocess
from pathlib import Path


DIGEST = re.compile(r"sha256:[0-9a-f]{64}")


def digest_of(reference):
    output = subprocess.check_output(["docker", "buildx", "imagetools", "inspect", reference], text=True)
    match = re.search(r"^Digest:\s+(sha256:[0-9a-f]{64})\s*$", output, re.MULTILINE)
    if not match:
        raise ValueError(f"No manifest digest reported for {reference}")
    return match.group(1)


def tag_latest(repository, digest):
    subprocess.run(["docker", "buildx", "imagetools", "create", "--tag",
                    f"{repository}:latest", f"{repository}@{digest}"], check=True)


def promote(version, pair):
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("Only a stable release version can be promoted")
    if len(pair) != 2 or not all(DIGEST.fullmatch(value) for value in pair.values()):
        raise ValueError("Two verified image digests are required")

    previous = {}
    for repo, digest in pair.items():
        if digest_of(f"{repo}:{version}") != digest:
            raise RuntimeError(f"{repo}:{version} moved after verification")
        previous[repo] = digest_of(f"{repo}:latest")
    receipt = "\n".join(f"{repo}:latest  {previous[repo]} -> {digest}" for repo, digest in pair.items())
    print(receipt, flush=True)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(summary).open("a") as report:
            report.write(f"Stable image digests for {version}\n\n```\n{receipt}\n```\n")

    attempted = []
    try:
        for repo, digest in pair.items():
            if previous[repo] != digest:
                if digest_of(f"{repo}:latest") != previous[repo]:
                    raise RuntimeError(f"{repo}:latest changed before promotion")
                # A lost command response can still mean the registry accepted the write.
                attempted.append(repo)
                tag_latest(repo, digest)
        for repo, digest in pair.items():
            if digest_of(f"{repo}:latest") != digest:
                raise RuntimeError(f"{repo}:latest did not resolve to the verified digest")
    except BaseException:
        failures = []
        for repo in reversed(attempted):
            try:
                current = digest_of(f"{repo}:latest")
                if current == previous[repo]:
                    continue
                if current != pair[repo]:
                    raise RuntimeError("latest changed independently")
                tag_latest(repo, previous[repo])
                if digest_of(f"{repo}:latest") != previous[repo]:
                    raise RuntimeError("restored digest could not be verified")
            except Exception as exc:
                failures.append(f"{repo}: {exc}")
        if failures:
            raise RuntimeError("Stable image rollback requires review: " + ", ".join(failures))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    parser.add_argument("backend_digest")
    parser.add_argument("frontend_digest")
    args = parser.parse_args()
    promote(args.version, {
        "ghcr.io/frontline-network/frontline-rcon-suite": args.backend_digest,
        "ghcr.io/frontline-network/frontline-rcon-suite-frontend": args.frontend_digest,
    })
