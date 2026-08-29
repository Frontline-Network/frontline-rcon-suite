from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKENDS = {f"backend_{index}" for index in range(1, 5)}
SUPERVISORS = {f"supervisor_{index}" for index in range(1, 5)}
BACKGROUND_WORKERS = {
    "mobile_push_worker",
    "discord_report_worker",
    "discord_moderation_worker",
    "frontline_background_worker",
}


class ComposeLoader(yaml.SafeLoader):
    pass


ComposeLoader.add_constructor(
    "!reset", lambda loader, node: loader.construct_sequence(node)
)


def _services():
    compose = yaml.load(
        (REPO_ROOT / "compose.mobile-admin.yaml").read_text(encoding="utf-8"),
        Loader=ComposeLoader,
    )
    return compose["services"]


def _assert_resources(service, *, cpus, memory, reserve_cpus, reserve_memory):
    resources = service["deploy"]["resources"]

    assert resources["limits"] == {"cpus": cpus, "memory": memory}
    assert resources["reservations"] == {
        "cpus": reserve_cpus,
        "memory": reserve_memory,
    }


def test_backends_have_a_bounded_restart_and_resource_envelope():
    services = _services()

    for name in BACKENDS:
        assert services[name]["restart"] == "on-failure:5"
        _assert_resources(
            services[name],
            cpus="${BACKEND_CPU_LIMIT:-1.0}",
            memory="${BACKEND_MEMORY_LIMIT:-1024M}",
            reserve_cpus="0.10",
            reserve_memory="256M",
        )


def test_supervisors_have_a_bounded_restart_and_resource_envelope():
    services = _services()

    for name in SUPERVISORS:
        assert services[name]["restart"] == "on-failure:5"
        _assert_resources(
            services[name],
            cpus="${SUPERVISOR_CPU_LIMIT:-1.5}",
            memory="${SUPERVISOR_MEMORY_LIMIT:-2048M}",
            reserve_cpus="0.20",
            reserve_memory="512M",
        )


def test_every_delivery_worker_has_the_same_resource_envelope():
    services = _services()

    for name in BACKGROUND_WORKERS:
        _assert_resources(
            services[name],
            cpus="${BACKGROUND_WORKER_CPU_LIMIT:-0.50}",
            memory="${BACKGROUND_WORKER_MEMORY_LIMIT:-512M}",
            reserve_cpus="0.05",
            reserve_memory="128M",
        )
