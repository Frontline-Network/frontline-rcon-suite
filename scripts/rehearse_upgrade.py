"""Rehearse a real image upgrade in an isolated PostgreSQL/Redis namespace.

prepare creates a new disposable environment, optionally from verified dumps.
verify applies the candidate twice and boots the old image again for rollback.
cleanup removes only containers whose recorded IDs and ownership label match.
No production containers, Compose files, ports, or volumes are accepted.
"""

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

LABEL = "frontline.upgrade-rehearsal"
PROBE = Path(__file__).with_name("upgrade_probe.py")


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024**2), b""):
            result.update(chunk)
    return result.hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


class Rehearsal:
    def __init__(self, directory):
        self.directory = directory.resolve()
        self.state_path = self.directory / "state.private.json"
        self.state = (
            json.loads(self.state_path.read_text())
            if self.state_path.exists()
            else None
        )

    def save(self):
        self.state_path.write_text(json.dumps(self.state, indent=2) + "\n")
        self.state_path.chmod(0o600)

    def emit(self, stage, **data):
        print(json.dumps({"stage": stage, **data}), flush=True)

    def command(self, arguments, *, data=None, timeout=120, log=None):
        result = subprocess.run(
            arguments, input=data, capture_output=True, text=True, timeout=timeout
        )
        if log:
            (self.directory / log).write_text(result.stdout + "\n" + result.stderr)
        if result.returncode:
            (self.directory / "last-error.private.log").write_text(
                result.stdout + "\n" + result.stderr
            )
            raise RuntimeError(
                "Rehearsal command failed; inspect last-error.private.log"
            )
        return result.stdout.strip()

    def inspect(self, reference, *, image=False):
        return json.loads(
            self.command(
                ["docker", *(["image"] if image else []), "inspect", reference]
            )
        )[0]

    def owned(self, kind):
        expected = self.state["containers"][kind]
        current = self.inspect(expected["id"])
        if (
            current["Id"] != expected["id"]
            or current["Config"]["Labels"].get(LABEL) != self.state["token"]
        ):
            raise RuntimeError("Container ownership changed; refusing to continue")
        if current["HostConfig"].get("PortBindings"):
            raise RuntimeError("Rehearsal containers must not publish ports")
        if kind == "postgres" and current["HostConfig"]["NetworkMode"] != "none":
            raise RuntimeError("Database namespace is no longer isolated")
        if (
            kind != "postgres"
            and current["HostConfig"]["NetworkMode"]
            != "container:" + self.state["containers"]["postgres"]["id"]
        ):
            raise RuntimeError("Rehearsal container joined an unexpected network")
        return current

    def start(
        self,
        kind,
        image,
        *,
        arguments=(),
        env=False,
        entrypoint=None,
        mounts=(),
        memory="1g",
        cpus="1",
    ):
        if kind in self.state["containers"]:
            raise RuntimeError("Container already tracked: " + kind)
        name = "rcon-upgrade-" + self.state["token"] + "-" + kind
        network = (
            "none"
            if kind == "postgres"
            else "container:" + self.owned("postgres")["Id"]
        )
        command = [
            "docker",
            "run",
            "--pull",
            "never",
            "-d",
            "--name",
            name,
            "--label",
            LABEL + "=" + self.state["token"],
            "--network",
            network,
            "--memory",
            memory,
            "--cpus",
            cpus,
        ]
        if env:
            command += ["--env-file", str(self.directory / "environment.private.env")]
            command += [
                "-e",
                "HLL_MAINTENANCE_CONTAINER=" + ("1" if kind == "maintenance" else ""),
            ]
            command += [
                "--tmpfs",
                "/logs:rw,mode=1777",
                "--tmpfs",
                "/static:rw,mode=1777",
            ]
        if kind == "postgres":
            command += ["-e", "POSTGRES_HOST_AUTH_METHOD=trust"]
        if entrypoint:
            command += ["--entrypoint", entrypoint]
        for source, target in mounts:
            command += ["--mount", f"type=bind,src={source},dst={target},readonly"]
        container_id = self.command(command + [image, *arguments])
        self.state["containers"][kind] = {"id": container_id, "name": name}
        self.save()
        self.owned(kind)

    def remove(self, kind):
        container = self.owned(kind)
        self.command(["docker", "rm", "-f", "-v", container["Id"]])
        del self.state["containers"][kind]
        self.save()

    def wait(self, kind, command, timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            current = self.owned(kind)
            if not current["State"]["Running"]:
                break
            test = subprocess.run(
                ["docker", "exec", current["Id"], *command],
                capture_output=True,
                timeout=10,
            )
            if test.returncode == 0:
                return
            time.sleep(2)
        self.command(
            ["docker", "logs", self.owned(kind)["Id"]],
            log=kind + "-startup.private.log",
        )
        raise RuntimeError(kind + " did not become ready")

    def probe(self, kind, mode):
        content = self.command(
            [
                "docker",
                "exec",
                "-i",
                "-w",
                "/code",
                self.owned(kind)["Id"],
                "python",
                "-",
                mode,
            ],
            data=PROBE.read_text(),
            timeout=600,
            log=mode + "-probe.private.log",
        )
        return json.loads(content.splitlines()[-1])

    def maintenance(self, image, stage):
        started = time.monotonic()
        self.start("maintenance", image, arguments=["maintenance"], env=True)
        self.wait(
            "maintenance",
            ["test", "-f", "/code/rconweb/maintenance-container-healthy"],
            900,
        )
        self.command(
            ["docker", "logs", self.owned("maintenance")["Id"]],
            log=stage + "-maintenance.private.log",
        )
        self.remove("maintenance")
        return round(time.monotonic() - started, 2)

    def web(self, image, stage):
        started = time.monotonic()
        self.start("web", image, arguments=["web"], env=True)
        self.wait("web", ["python", "/code/scripts/backend_healthcheck.py"], 180)
        result = {"ready_seconds": round(time.monotonic() - started, 2)}
        result.update(self.probe("web", "http"))
        result["preservation"] = self.probe("web", "snapshot")
        self.command(
            ["docker", "logs", self.owned("web")["Id"]], log=stage + "-web.private.log"
        )
        self.remove("web")
        return result

    def prepare(self, args):
        if self.state or self.directory.exists():
            raise RuntimeError("Choose a new, empty state directory")
        self.directory.mkdir(mode=0o700, parents=True)
        self.state = {
            "token": secrets.token_hex(6),
            "started_at": now(),
            "containers": {},
            "stages": {},
        }
        self.save()
        images = {
            name: self.inspect(getattr(args, name + "_image"), image=True)["Id"]
            for name in ("source", "postgres", "redis")
        }
        self.state["images"] = images
        for kind in ("backup", "redis_backup"):
            filename = getattr(args, kind)
            checksum = getattr(args, kind + "_sha256")
            if bool(filename) != bool(checksum):
                raise RuntimeError(
                    "Every supplied backup requires its expected SHA-256"
                )
            if filename:
                path = Path(filename).resolve(strict=True)
                if (
                    not path.is_file()
                    or not re.fullmatch("[0-9a-f]{64}", checksum)
                    or digest(path) != checksum
                ):
                    raise RuntimeError("Backup checksum verification failed")
                self.state[kind] = {
                    "path": str(path),
                    "sha256": checksum,
                    "bytes": path.stat().st_size,
                }
        required = max(4 * 1024**3, self.state.get("backup", {}).get("bytes", 0) * 10)
        if shutil.disk_usage(self.directory).free < required:
            raise RuntimeError("Insufficient temporary disk space for the restore")
        token = self.state["token"]
        environment = {
            "CRCON_UPGRADE_REHEARSAL": "isolated",
            "REHEARSAL_USERNAME": "upgrade-fixture-" + token,
            "REHEARSAL_PASSWORD": secrets.token_urlsafe(32),
            "REHEARSAL_API_KEY": secrets.token_urlsafe(48),
            "RCONWEB_API_SECRET": secrets.token_hex(32),
            "DONT_SEED_ADMIN_USER": "1",
            "HLL_DB_URL": "postgresql://postgres@127.0.0.1:5432/postgres",
            "HLL_DB_USER": "postgres",
            "HLL_DB_PASSWORD": "isolated",
            "HLL_DB_HOST": "127.0.0.1",
            "HLL_DB_HOST_PORT": "5432",
            "HLL_DB_NAME": "postgres",
            "HLL_REDIS_URL": "redis://127.0.0.1:6379/3",
            "HLL_REDIS_HOST": "127.0.0.1",
            "HLL_REDIS_PORT": "6379",
            "HLL_REDIS_DB": "3",
            "SERVER_NUMBER": "3",
            "HLL_HOST": "127.0.0.1",
            "HLL_PORT": "1",
            "HLL_PASSWORD": "isolated",
            "LOGGING_PATH": "/tmp/",
            "LOGGING_FILENAME": "rehearsal.log",
            "NB_API_WORKERS": "1",
            "NB_API_THREADS": "2",
            "HLL_API_SERVER_MODE": args.api_mode,
            "HLL_RCON_VERSION": "2",
            "HLL_GAME": args.game,
        }
        self.state["environment_sha256"] = hashlib.sha256(
            json.dumps(environment, sort_keys=True).encode()
        ).hexdigest()
        self.state["game"] = args.game
        self.state["api_mode"] = args.api_mode
        (self.directory / "environment.private.env").write_text(
            "".join(k + "=" + v + "\n" for k, v in environment.items())
        )
        mounts = (
            [(self.state["backup"]["path"], "/backup.dump")]
            if "backup" in self.state
            else []
        )
        self.start("postgres", images["postgres"], mounts=mounts, memory="3g", cpus="2")
        self.wait("postgres", ["pg_isready", "-U", "postgres"], 90)
        if "backup" in self.state:
            self.emit("restore_started")
            self.command(
                [
                    "docker",
                    "exec",
                    self.owned("postgres")["Id"],
                    "pg_restore",
                    "--exit-on-error",
                    "--no-owner",
                    "--no-privileges",
                    "-U",
                    "postgres",
                    "-d",
                    "postgres",
                    "/backup.dump",
                ],
                timeout=3600,
                log="restore.private.log",
            )
        redis_mounts = (
            [(self.state["redis_backup"]["path"], "/backup.rdb")]
            if "redis_backup" in self.state
            else []
        )
        redis_script = (
            "cp /backup.rdb /data/dump.rdb && " if redis_mounts else ""
        ) + "exec redis-server --bind 127.0.0.1 --save '' --appendonly no"
        self.start(
            "redis",
            images["redis"],
            entrypoint="sh",
            arguments=["-c", redis_script],
            mounts=redis_mounts,
            memory="768m",
            cpus="0.5",
        )
        self.wait("redis", ["redis-cli", "ping"], 90)
        self.emit("source_maintenance_started")
        self.state["stages"]["source_maintenance_seconds"] = self.maintenance(
            images["source"], "source"
        )
        self.start(
            "fixture",
            images["source"],
            env=True,
            entrypoint="sleep",
            arguments=["infinity"],
        )
        self.probe("fixture", "seed")
        self.remove("fixture")
        self.state["stages"]["source"] = self.web(images["source"], "source")
        self.state["prepared_at"] = now()
        self.save()
        self.emit(
            "prepared",
            state_directory=str(self.directory),
            network="none",
            source_image=images["source"],
        )

    def verify(self, args):
        if (
            not self.state
            or not self.state.get("prepared_at")
            or self.state.get("verified_at")
        ):
            raise RuntimeError("A prepared, unverified environment is required")
        self.owned("postgres")
        self.owned("redis")
        candidate = self.inspect(args.candidate_image, image=True)["Id"]
        self.state["images"]["candidate"] = candidate
        self.save()
        baseline = self.state["stages"]["source"]["preservation"]
        for stage in ("candidate", "candidate_repeat"):
            self.emit(stage + "_started")
            self.state["stages"][stage + "_maintenance_seconds"] = self.maintenance(
                candidate, stage
            )
            result = self.web(candidate, stage)
            self.state["stages"][stage] = result
            self.save()
            if result["preservation"] != baseline:
                raise RuntimeError("Preserved customer data changed: " + stage)
        # Code rollback only. Never run old migrations against a new schema.
        self.emit("rollback_started")
        rollback = self.web(self.state["images"]["source"], "rollback")
        if rollback["preservation"] != baseline:
            raise RuntimeError("Rollback changed preserved customer data")
        self.state["stages"]["rollback"] = rollback
        self.state["verified_at"] = now()
        self.save()
        receipt = {
            k: self.state[k]
            for k in (
                "started_at",
                "prepared_at",
                "verified_at",
                "game",
                "api_mode",
                "images",
                "stages",
            )
        }
        receipt.update(
            network="none",
            backup_sha256=self.state.get("backup", {}).get("sha256"),
            production_changed=False,
        )
        (self.directory / "verified.json").write_text(json.dumps(receipt, indent=2))
        self.emit("verified", receipt=str(self.directory / "verified.json"))

    def cleanup(self):
        if not self.state:
            raise RuntimeError("No owned environment to clean up")
        for kind in reversed(list(self.state["containers"])):
            self.remove(kind)
        self.state["cleaned_at"] = now()
        self.save()
        self.emit("cleaned", backups_preserved=True)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, required=True)
    sub = parser.add_subparsers(dest="action", required=True)
    prepare = sub.add_parser("prepare")
    for name in ("source", "postgres", "redis"):
        prepare.add_argument("--" + name + "-image", required=True)
    prepare.add_argument("--game", choices=("hll", "hllv"), default="hll")
    prepare.add_argument("--api-mode", choices=("split", "unified"), default="split")
    for name in ("backup", "redis-backup"):
        prepare.add_argument("--" + name)
        prepare.add_argument("--" + name + "-sha256")
    verify = sub.add_parser("verify")
    verify.add_argument("--candidate-image", required=True)
    sub.add_parser("cleanup")
    args = parser.parse_args()
    environment = Rehearsal(args.state_dir)
    getattr(environment, args.action)(*(() if args.action == "cleanup" else (args,)))


if __name__ == "__main__":
    main()
