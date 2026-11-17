"""Preserve stopped numbered server services during an existing deployment."""

import argparse
import json
import re
import sys

SERVER_SERVICE = re.compile(r"(backend|frontend|supervisor)_([1-9][0-9]*)\Z")


def select_services(configured: list[str], running: set[str]) -> list[str]:
    result = []
    for service in configured:
        match = SERVER_SERVICE.fullmatch(service)
        if match and service not in running:
            continue
        if match and match[1] != "backend":
            backend = f"backend_{match[2]}"
            if backend not in running or backend not in configured:
                raise ValueError(f"Running {service} has no running configured {backend}")
        result.append(service)
    return result


def verify_dependencies(compose: dict, selected: list[str]) -> None:
    services = compose.get("services", {})
    selected_set = set(selected)
    seen = set()
    pending = list(selected)
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        if name not in services:
            raise ValueError(f"Selected or required service {name} is absent from Compose")
        for dependency in (services[name].get("depends_on") or {}):
            if SERVER_SERVICE.fullmatch(dependency) and dependency not in selected_set:
                raise ValueError(f"{name} would start excluded server service {dependency}")
            pending.append(dependency)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configured", help="Newline-separated Compose service names")
    parser.add_argument("--running", help="Newline-separated running Compose service names")
    parser.add_argument("--check-dependencies", action="store_true")
    parser.add_argument("services", nargs="*")
    args = parser.parse_args()
    try:
        if args.check_dependencies:
            verify_dependencies(json.load(sys.stdin), args.services)
            return
        if args.configured is None or args.running is None or args.services:
            parser.error("selection requires --configured and --running")
        result = select_services(args.configured.splitlines(), set(args.running.splitlines()))
    except ValueError as exc:
        parser.exit(1, f"Unsafe server service state: {exc}\n")
    print("\n".join(result))


if __name__ == "__main__":
    main()
