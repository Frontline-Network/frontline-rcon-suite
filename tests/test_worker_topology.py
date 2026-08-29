from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SPLIT_WORKERS = {
    "mobile_push_worker",
    "discord_report_worker",
    "discord_moderation_worker",
}


class ComposeLoader(yaml.SafeLoader):
    pass


ComposeLoader.add_constructor(
    "!reset", lambda loader, node: loader.construct_sequence(node)
)
ComposeLoader.add_constructor(
    "!override", lambda loader, node: loader.construct_sequence(node)
)


def _load_compose(filename):
    return yaml.load(
        (REPO_ROOT / filename).read_text(encoding="utf-8"),
        Loader=ComposeLoader,
    )


def test_compose_profiles_make_worker_topologies_mutually_exclusive():
    mobile_compose = _load_compose("compose.mobile-admin.yaml")
    topology_compose = _load_compose("compose.combined-workers.yaml")

    assert mobile_compose["services"]["frontline_background_worker"]["profiles"] == [
        "combined-workers"
    ]
    for service in SPLIT_WORKERS:
        assert topology_compose["services"][service]["profiles"] == [
            "split-background-workers"
        ]


def test_deploy_script_reconciles_both_worker_topologies():
    deploy_script = (REPO_ROOT / "scripts" / "deploy_frontline.sh").read_text(
        encoding="utf-8"
    )

    assert "FRONTLINE_BACKGROUND_WORKER_MODE" in deploy_script
    assert "Background worker topology: $background_worker_mode" in deploy_script
    assert "compose_all_worker_profiles rm --stop --force" in deploy_script
    for service in SPLIT_WORKERS | {"frontline_background_worker"}:
        assert service in deploy_script


def test_new_installations_default_to_automatic_worker_migration():
    default_environment = (REPO_ROOT / "default.env").read_text(encoding="utf-8")

    assert "FRONTLINE_BACKGROUND_WORKER_MODE=auto" in default_environment.splitlines()
