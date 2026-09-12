import io
import json
import shutil
import subprocess
import tarfile
import time
from pathlib import Path

from sqlalchemy import and_, insert, or_, select, update

from .artifacts import canonical
from .comparison import compare, validate_metrics, validate_tables
from .database import attempts, runs, uid


class UnavailableImage(Exception):
    pass


class Docker:
    def __init__(self, settings):
        self.settings = settings
        self.prefix = ["docker"] + (["--context", settings.docker_context] if settings.docker_context else [])

    def command(self, args, timeout=30, check=True):
        r = subprocess.run(self.prefix + args, capture_output=True, text=True, timeout=timeout)
        if check and r.returncode:
            raise RuntimeError(r.stderr[-2000:] or "Docker command failed")
        return r

    def engine_id(self):
        return self.command(["info", "--format", "{{.ID}}"]).stdout.strip()

    def image_id(self):
        return self.command(["image", "inspect", self.settings.image, "--format", "{{.Id}}"]).stdout.strip()

    def inspect(self, name):
        r = self.command(["inspect", name], check=False)
        if r.returncode:
            if "no such object" in r.stderr.lower() or "no such container" in r.stderr.lower():
                return None
            raise RuntimeError(r.stderr[-2000:])
        return json.loads(r.stdout)[0]

    def launch(self, name, run):
        available = self.command(["image", "inspect", run["body"]["image_id"]], check=False)
        if available.returncode:
            if "no such image" in available.stderr.lower():
                raise UnavailableImage(
                    "The registered image is absent on this worker. Rebuild or load its exact revision."
                )
            raise RuntimeError(available.stderr[-2000:])
        limits = run["body"]["limits"]
        args = [
            "create",
            "--name",
            name,
            "--platform",
            "linux/amd64",
            "--network",
            "none",
            "--read-only",
            "--user",
            "1000:1000",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--pids-limit",
            "96",
            "--memory",
            f"{limits['memory_mib']}m",
            "--memory-swap",
            f"{limits['memory_mib']}m",
            "--cpus",
            str(limits["cpu"]),
            "--ulimit",
            "nofile=256:256",
            "--ulimit",
            "fsize=67108864:67108864",
            "--tmpfs",
            "/work:rw,nosuid,nodev,noexec,size=128m,uid=1000,gid=1000,mode=0700",
            "--tmpfs",
            "/tmp:rw,nosuid,nodev,noexec,size=16m,uid=1000,gid=1000,mode=0700",
            "--log-driver",
            "json-file",
            "--log-opt",
            "max-size=1m",
            "--log-opt",
            "max-file=1",
            "--label",
            "research.workbench=true",
            "--label",
            f"research.run={run['id']}",
            "--label",
            f"research.epoch={run['epoch']}",
            "-e",
            "PLAN_JSON=" + canonical(run["body"]["plan"]).decode(),
            "-e",
            f"WALL_SECONDS={limits['wall_seconds']}",
            run["body"]["image_id"],
        ]
        self.command(args, timeout=60)

    def start(self, name):
        self.command(["start", name])

    def done(self, name):
        return self.command(["exec", name, "test", "-f", "/work/done"], check=False).returncode == 0

    def collect(self, name, dest):
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True, exist_ok=True)
        # docker cp cannot reliably see tmpfs mounts on every daemon. Read from the live namespace.
        result = subprocess.run(
            self.prefix + ["exec", name, "tar", "-C", "/work/output", "-cf", "-", "."],
            capture_output=True,
            timeout=60,
        )
        if result.returncode or len(result.stdout) > 100 * 1024 * 1024:
            raise ValueError("Output collection failed or exceeded 100 MiB")
        with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as archive:
            for item in archive:
                path = Path(item.name)
                if item.isdir():
                    continue
                if not item.isfile() or path.is_absolute() or ".." in path.parts or len(path.parts) > 2:
                    raise ValueError("Unsafe output archive member")
                target = dest / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.extractfile(item).read())
        recipe = self.command(["exec", name, "cat", "/app/run.R"]).stdout.encode()
        if len(recipe) > 100_000:
            raise ValueError("Unexpected recipe size")
        (dest / "recipe.R").write_bytes(recipe)
        for filename in ("locked-packages.json", "Dockerfile", "entrypoint.sh", "law-samples.csv"):
            result = self.command(["exec", name, "cat", "/app/" + filename], check=False)
            if result.returncode == 0:
                (dest / filename).write_text(result.stdout)

    def stop(self, name):
        current = self.inspect(name)
        if current and current["State"]["Running"]:
            self.command(["stop", "--time", "3", name])
        current = self.inspect(name)
        if current and current["State"]["Running"]:
            raise RuntimeError("Container termination not confirmed")

    def remove(self, name):
        self.command(["rm", name], check=False)


class Worker:
    def __init__(self, service, docker=None, identity=None):
        self.service, self.db, self.settings = service, service.db, service.settings
        self.docker = docker or Docker(self.settings)
        self.identity = identity or "worker-" + uid()
        self.engine_id = self.docker.engine_id() if hasattr(self.docker, "engine_id") else "test-runtime"

    def name(self, run):
        return f"research-{run['id']}-{run['epoch']}"

    def claim(self):
        now = time.time()
        with self.db.transaction() as c:
            q = (
                select(runs)
                .where(
                    or_(
                        runs.c.state == "queued",
                        and_(
                            runs.c.state.in_(["running", "cancel_requested"]),
                            or_(runs.c.owner == self.identity, runs.c.lease_until < now),
                            runs.c.body["runtime_id"].as_string() == self.engine_id,
                        ),
                    )
                )
                .order_by(runs.c.created)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            run = c.execute(q).mappings().first()
            if not run:
                return None
            run = dict(run)
            queued = run["state"] == "queued"
            epoch = run["epoch"] + 1 if queued else run["epoch"]
            values = {
                "owner": self.identity,
                "epoch": epoch,
                "lease_until": now + self.settings.lease_seconds,
                "updated": now,
            }
            if queued:
                values["state"] = "running"
                values["body"] = {**run["body"], "runtime_id": self.engine_id}
            changed = c.execute(
                update(runs)
                .where(
                    runs.c.id == run["id"],
                    runs.c.epoch == run["epoch"],
                    runs.c.state == run["state"],
                    runs.c.lease_until == run["lease_until"],
                )
                .values(**values)
            ).rowcount
            if changed != 1:
                return None
            run.update(values)
            if queued:
                c.execute(
                    insert(attempts).values(
                        run_id=run["id"],
                        epoch=epoch,
                        body={"started": now, "container": self.name(run), "phase": "intent"},
                    )
                )
                self.db.emit(
                    c, run["workspace_id"], "run.started", self.identity, {"epoch": epoch}, run["id"]
                )
            return run

    def owned(self, c, run):
        current = self.db.row(c, runs, run["id"])
        return (
            current
            and current["owner"] == self.identity
            and current["epoch"] == run["epoch"]
            and current["state"] in ("running", "cancel_requested")
        )

    def finish(self, run, state, extra):
        with self.db.transaction() as c:
            if not self.owned(c, run):
                return False
            current = dict(self.db.row(c, runs, run["id"]))
            if current["cancel_requested"]:
                state = "cancelled"
            c.execute(
                update(runs)
                .where(runs.c.id == run["id"])
                .values(
                    state=state,
                    body={**current["body"], **extra},
                    owner=None,
                    lease_until=0,
                    updated=time.time(),
                )
            )
            self.db.emit(
                c,
                run["workspace_id"],
                "run." + state,
                self.identity,
                {"epoch": run["epoch"], "diagnostic": extra.get("diagnostic")},
                run["id"],
            )
        return True

    def attempt(self, run):
        with self.db.transaction() as c:
            return c.execute(
                select(attempts.c.body).where(
                    attempts.c.run_id == run["id"], attempts.c.epoch == run["epoch"]
                )
            ).scalar_one()

    def save_attempt(self, run, body):
        with self.db.transaction() as c:
            if not self.owned(c, run):
                return False
            c.execute(
                update(attempts)
                .where(attempts.c.run_id == run["id"], attempts.c.epoch == run["epoch"])
                .values(body=body)
            )
        return True

    def retry_or_fail(self, run, diagnostic):
        if run["epoch"] >= self.settings.max_attempts or run["cancel_requested"]:
            return self.finish(run, "failed", {"diagnostic": diagnostic})
        with self.db.transaction() as c:
            if not self.owned(c, run):
                return False
            c.execute(
                update(runs)
                .where(runs.c.id == run["id"])
                .values(state="queued", owner=None, lease_until=0, updated=time.time())
            )
            self.db.emit(
                c,
                run["workspace_id"],
                "run.retry_queued",
                self.identity,
                {"reason": diagnostic, "epoch": run["epoch"]},
                run["id"],
            )

    def tick(self):
        run = self.claim()
        if not run:
            return False
        name = self.name(run)
        attempt = self.attempt(run)
        # A sealed receipt survives a crash between stopping the container and committing final status.
        if attempt.get("phase") == "sealed":
            self.docker.stop(name)
            if self.finish(run, attempt["outcome"], attempt["receipt"]):
                self.docker.remove(name)
            return True
        info = self.docker.inspect(name)
        if run["cancel_requested"]:
            self.docker.stop(name)
            if self.finish(run, "cancelled", {"diagnostic": "Sandbox termination confirmed"}):
                self.docker.remove(name)
            return True
        if info is None:
            if attempt["phase"] == "intent":
                try:
                    self.docker.launch(name, run)
                except UnavailableImage as error:
                    self.finish(run, "failed", {"diagnostic": str(error)})
                    return True
                self.save_attempt(run, {**attempt, "phase": "created"})
                self.docker.start(name)
            else:
                self.retry_or_fail(run, "Sandbox was lost before outputs could be sealed")
            return True
        if (
            info["Config"]["Labels"].get("research.run") != run["id"]
            or info["Image"] != run["body"]["image_id"]
        ):
            raise RuntimeError("Sandbox identity does not match durable intent")
        if time.time() - attempt["started"] > run["body"]["limits"]["wall_seconds"] + 60:
            self.docker.stop(name)
            if self.finish(run, "failed", {"diagnostic": "Supervisor wall-clock limit exceeded"}):
                self.docker.remove(name)
            return True
        if info["State"]["Status"] == "created":
            self.docker.start(name)
            return True
        if info["State"]["Running"] and self.docker.done(name):
            dest = self.settings.data_dir / "attempts" / name
            try:
                self.docker.collect(name, dest)
                code = int((dest / "exit-code").read_text().strip())
                artifacts = self.service.store.collect(dest)
            except (ValueError, FileNotFoundError) as error:
                self.docker.stop(name)
                if self.finish(run, "failed", {"diagnostic": "Unsafe or incomplete outputs: " + str(error)}):
                    self.docker.remove(name)
                return True
            receipt = {
                "artifacts": artifacts,
                "exit_code": code,
                "duration_seconds": time.time() - attempt["started"],
                "runtime": {"image_id": info["Image"], "platform": "linux/amd64", "container_id": info["Id"]},
            }
            outcome = "succeeded" if code == 0 else "failed"
            if code == 0:
                try:
                    metrics = validate_metrics(
                        self.service.store.read(artifacts["metrics.json"]["sha256"]), run["body"]["plan"]
                    )
                    validate_tables(self.service.store, artifacts, metrics, run["body"]["plan"])
                    receipt["comparison"] = compare(metrics, run["body"]["plan"])
                    if not self.service.store.read(artifacts["figure.png"]["sha256"]).startswith(
                        b"\x89PNG\r\n\x1a\n"
                    ):
                        raise ValueError("Invalid figure output")
                except (ValueError, KeyError) as e:
                    outcome = "failed"
                    receipt["diagnostic"] = "Output validation failed: " + str(e)
            else:
                receipt["diagnostic"] = (
                    "Time limit exceeded" if code == 124 else f"Scientific process exited with status {code}"
                )
            if self.save_attempt(run, {**attempt, "phase": "sealed", "receipt": receipt, "outcome": outcome}):
                self.docker.stop(name)
                if self.finish(run, outcome, receipt):
                    self.docker.remove(name)
            return True
        if not info["State"]["Running"]:
            diagnostic = (
                "Memory limit exceeded"
                if info["State"].get("OOMKilled")
                else "Sandbox exited before completion signal"
            )
            # OOM is a deterministic budget failure, not an automatic spend/retry trigger.
            if self.finish(run, "failed", {"diagnostic": diagnostic, "container_state": info["State"]}):
                self.docker.remove(name)
            return True
        if time.time() - attempt["started"] > run["body"]["limits"]["wall_seconds"] + 60:
            self.docker.stop(name)
            if self.finish(run, "failed", {"diagnostic": "Supervisor wall-clock limit exceeded"}):
                self.docker.remove(name)
        return True
