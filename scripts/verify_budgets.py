"""Exercise timeout and OOM reporting with bounded, trusted fault-injection images."""

import json
import shutil
import tempfile
import time
import uuid
from pathlib import Path

from workbench.cli import make_service
from workbench.config import ROOT, Settings
from workbench.runner import Docker, Worker
from workbench.schemas import Limits, LockRequest, PlanCreate, RunCreate
from workbench.service import REQUIRED_REVIEW

settings = Settings()
docker = Docker(settings)
base = docker.image_id()
results = {}
with tempfile.TemporaryDirectory(prefix="budget-check-", dir=settings.data_dir) as directory:
    root = Path(directory)
    for kind, code, entrypoint, diagnostic in [
        ("timeout", "Sys.sleep(60)\n", "", "Time limit exceeded"),
        (
            "oom",
            "x <- numeric(100000000); Sys.sleep(60)\n",
            '\nENTRYPOINT ["Rscript", "/app/run.R"]\n',
            "Memory limit exceeded",
        ),
    ]:
        context = root / kind
        context.mkdir()
        (context / "run.R").write_text(code)
        tag = "research-budget-check:" + uuid.uuid4().hex
        base_tag = "research-budget-base:" + uuid.uuid4().hex
        name = None
        service = None
        try:
            docker.command(["image", "tag", base, base_tag])
            (context / "Dockerfile").write_text(f"FROM {base_tag}\nCOPY run.R /app/run.R\n" + entrypoint)
            docker.command(
                ["build", "--platform", "linux/amd64", "--network", "none", "-t", tag, str(context)],
                timeout=60,
            )
            identity = docker.command(["image", "inspect", tag, "--format", "{{.Id}}"]).stdout.strip()
            data = root / (kind + "-data")
            (data / "sources").mkdir(parents=True)
            shutil.copyfile(settings.data_dir / "sources/law2018.json", data / "sources/law2018.json")
            service = make_service(Settings(data_dir=data, docker_context=settings.docker_context))
            worker = Worker(service, docker)
            w = service.workspace("local", "Budget fault injection")
            p = service.new_plan("local", PlanCreate(workspace_id=w, title=kind))
            service.lock("local", p["id"], LockRequest(expected_revision=1, reviewed_fields=REQUIRED_REVIEW))
            run = service.submit(
                "local",
                RunCreate(plan_id=p["id"], limits=Limits(memory_mib=256, cpu=1, wall_seconds=5)),
                kind,
                identity,
            )
            deadline = time.monotonic() + 75
            while time.monotonic() < deadline:
                worker.tick()
                with service.db.transaction() as c:
                    run = service.get_run(c, "local", run["id"])
                name = worker.name(run)
                if run["state"] in ("failed", "succeeded", "cancelled"):
                    break
                time.sleep(0.5)
            assert run["state"] == "failed", run
            assert run["body"]["diagnostic"] == diagnostic, run["body"]
            assert run["epoch"] == 1, "A deterministic budget failure must not retry"
            assert docker.inspect(name) is None, "Terminal status left a container behind"
            results[kind] = {
                "state": run["state"],
                "diagnostic": diagnostic,
                "attempts": run["epoch"],
                "container_removed": True,
                "exit_code": run["body"].get("exit_code"),
                "container_state": run["body"].get("container_state"),
            }
            print(kind, diagnostic, flush=True)
        finally:
            if name:
                docker.stop(name)
                docker.remove(name)
            docker.command(["image", "rm", tag], check=False)
            docker.command(["image", "rm", base_tag], check=False)
            if service:
                service.db.engine.dispose()
receipt = {
    "date": "2026-09-11",
    "base_image_id": base,
    "scope": "Actual Docker budget faults using temporary curated test images; no application runtime registration changed",
    "results": results,
}
(ROOT / "evidence/budget-verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
