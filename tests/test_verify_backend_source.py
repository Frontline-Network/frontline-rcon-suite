import io
import tarfile

import pytest

from scripts.verify_backend_source import REQUIRED, compare


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "image"
    root.mkdir()
    files = {name: f"content of {name}\n".encode() for name in REQUIRED}
    files["rcon/weapons.py"] = b"weapon = 'example'\n"
    files["rconweb/static/logo.png"] = b"\x89PNG\r\n\x1a\n"
    archive = tmp_path / "source.tar"
    with tarfile.open(archive, "w") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    return root, archive


def test_identical_source_and_text_line_endings_are_accepted(source):
    root, archive = source
    path = root / "rcon/weapons.py"
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert compare(archive, root) == []


def test_stale_and_missing_runtime_files_are_reported(source):
    root, archive = source
    (root / "rcon/weapons.py").write_text("old catalog\n")
    (root / "rconweb/manage.py").unlink()
    errors = compare(archive, root)
    assert "Different file: rcon/weapons.py" in errors
    assert "Missing or non-regular file: rconweb/manage.py" in errors


def test_extra_python_file_and_binary_differences_are_reported(source):
    root, archive = source
    (root / "rcon/obsolete.py").write_text("pass\n")
    (root / "rconweb/static/logo.png").write_bytes(b"\x89PNG\n\x1a\n")
    errors = compare(archive, root)
    assert "Unexpected Python file: rcon/obsolete.py" in errors
    assert "Different file: rconweb/static/logo.png" in errors


def test_incomplete_and_unsafe_archives_are_rejected(tmp_path):
    archive = tmp_path / "bad.tar"
    with tarfile.open(archive, "w") as tar:
        info = tarfile.TarInfo("../escape.py")
        info.size = 0
        tar.addfile(info, io.BytesIO())
    with pytest.raises(ValueError, match="Unsafe archive path"):
        compare(archive, tmp_path)
    with tarfile.open(archive, "w"):
        pass
    with pytest.raises(ValueError, match="Incomplete source archive"):
        compare(archive, tmp_path)
