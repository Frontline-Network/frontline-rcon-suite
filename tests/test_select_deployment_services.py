import pytest

from scripts.select_deployment_services import select_services, verify_dependencies


def test_stopped_server_definitions_are_not_started():
    configured = ["redis", "postgres"] + [
        f"{kind}_{number}" for number in range(1, 5)
        for kind in ("backend", "frontend", "supervisor")
    ]
    running = {f"{kind}_{number}" for number in (3, 4)
               for kind in ("backend", "frontend", "supervisor")}
    selected = select_services(configured, running)
    assert selected == ["redis", "postgres"] + [name for name in configured if name in running]


def test_stopped_frontend_remains_stopped_when_its_backend_is_running():
    assert select_services(["backend_1", "frontend_1"], {"backend_1"}) == ["backend_1"]


@pytest.mark.parametrize("running", [{"frontend_1"}, {"supervisor_1"}])
def test_inconsistent_server_state_does_not_start_its_backend(running):
    with pytest.raises(ValueError, match="no running configured backend_1"):
        select_services(["backend_1", "frontend_1", "supervisor_1"], running)


def test_transitive_dependencies_cannot_start_an_excluded_server():
    compose = {"services": {
        "backend_3": {"depends_on": {"maintenance": {}}},
        "maintenance": {"depends_on": {"backend_1": {}}},
        "backend_1": {},
    }}
    with pytest.raises(ValueError, match="would start excluded server service backend_1"):
        verify_dependencies(compose, ["backend_3", "maintenance"])
    verify_dependencies(compose, ["backend_3", "maintenance", "backend_1"])


def test_missing_dependency_is_rejected():
    with pytest.raises(ValueError, match="absent from Compose"):
        verify_dependencies({"services": {"backend_3": {"depends_on": ["redis"]}}}, ["backend_3"])
