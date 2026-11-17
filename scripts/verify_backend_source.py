"""Compare a candidate image's runtime files against a trusted Git archive.

Run inside the candidate with a read-only archive made from the target commit.
No services, databases, or game-server connections are used.
"""

import argparse
import hashlib
import tarfile
from pathlib import Path, PurePosixPath

TEXT_SUFFIXES = {".py", ".js", ".json", ".html", ".txt", ".css", ".sh", ".md", ".ini", ".mako"}
TEXT_NAMES = {"LICENSE", "requirements.lock", "requirements-vcs.txt"}
REQUIRED = {
    "rcon/models.py", "rconweb/manage.py", "alembic/env.py",
    "scripts/deploy_frontline.sh", "entrypoint.sh", "manage.py",
}
PYTHON_ROOTS = ("rcon", "rconweb", "alembic", "scripts")


def _digest(data: bytes, name: str) -> bytes:
    path = PurePosixPath(name)
    if path.suffix in TEXT_SUFFIXES or path.name in TEXT_NAMES:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).digest()


def compare(archive_path: Path, root: Path) -> list[str]:
    errors = []
    expected = set()
    with tarfile.open(archive_path, "r:") as archive:
        for member in archive:
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts or not path.parts:
                raise ValueError(f"Unsafe archive path: {member.name}")
            if member.isdir():
                continue
            if not member.isfile() or member.name in expected:
                raise ValueError(f"Unsupported or duplicate archive entry: {member.name}")
            expected.add(member.name)
            destination = root.joinpath(*path.parts)
            if (not destination.is_file() or destination.is_symlink()
                    or not destination.resolve().is_relative_to(root.resolve())):
                errors.append(f"Missing or non-regular file: {member.name}")
                continue
            source = archive.extractfile(member)
            if source is None:
                raise ValueError(f"Unreadable archive entry: {member.name}")
            if _digest(source.read(), member.name) != _digest(destination.read_bytes(), member.name):
                errors.append(f"Different file: {member.name}")
    if not REQUIRED.issubset(expected):
        raise ValueError(f"Incomplete source archive: {sorted(REQUIRED - expected)}")
    for directory in PYTHON_ROOTS:
        for path in (root / directory).rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            relative = path.relative_to(root).as_posix()
            if relative not in expected:
                errors.append(f"Unexpected Python file: {relative}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--root", type=Path, default=Path("/code"))
    args = parser.parse_args()
    errors = compare(args.archive, args.root)
    if errors:
        print("Backend image does not match the target source:")
        print("\n".join(errors))
        raise SystemExit(1)
    print("Backend image runtime source matches the target Git archive.")


if __name__ == "__main__":
    main()
