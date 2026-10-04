import importlib.util
from pathlib import Path
from subprocess import CompletedProcess


SPEC = importlib.util.spec_from_file_location(
    "frontline_version", Path(__file__).parents[1] / "rcon" / "version.py"
)
assert SPEC and SPEC.loader
version_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(version_module)


def test_configured_version_is_preferred_without_invoking_git(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("git must not be invoked for a deployed version")

    monkeypatch.setattr(version_module, "run", fail_if_called)

    assert version_module.resolve_version({"CRCON_VERSION": " v0.3.9 "}) == "v0.3.9"


def test_git_version_is_used_for_local_development(monkeypatch):
    monkeypatch.setattr(
        version_module,
        "run",
        lambda *args, **kwargs: CompletedProcess(args[0], 0, b"v0.3.9-2-gabc\n", b""),
    )

    assert version_module.resolve_version({}) == "v0.3.9-2-gabc"


def test_missing_deployment_and_git_version_returns_unknown(monkeypatch):
    monkeypatch.setattr(
        version_module,
        "run",
        lambda *args, **kwargs: CompletedProcess(args[0], 128, b"", b"not a repo"),
    )

    assert version_module.resolve_version({}) == "unknown"


def test_baked_image_version_wins_over_stale_compose_environment(monkeypatch, tmp_path):
    version_file = tmp_path / "release_version"
    version_file.write_text("v0.8.8\n")
    monkeypatch.setattr(version_module, "IMAGE_VERSION_PATH", version_file)
    assert version_module.resolve_version({"CRCON_VERSION": "v0.8.7"}) == "v0.8.8"


def test_unknown_local_image_metadata_retains_configured_version(monkeypatch, tmp_path):
    version_file = tmp_path / "release_version"
    version_file.write_text("unknown\n")
    monkeypatch.setattr(version_module, "IMAGE_VERSION_PATH", version_file)
    assert version_module.resolve_version({"CRCON_VERSION": "v0.8.8"}) == "v0.8.8"
