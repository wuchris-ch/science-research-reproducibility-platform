"""Observe confinement and cancellation using an actual scientific sandbox."""

import json
import shutil
import tempfile
from pathlib import Path

from workbench.cli import make_service
from workbench.config import ROOT, Settings
from workbench.runner import Docker, Worker
from workbench.schemas import Limits, LockRequest, PlanCreate, RunCreate
from workbench.service import REQUIRED_REVIEW

settings = Settings()
docker = Docker(settings)
with tempfile.TemporaryDirectory(prefix="runtime-check-", dir=settings.data_dir) as directory:
    data = Path(directory)
    (data / "sources").mkdir()
    shutil.copyfile(settings.data_dir / "sources/law2018.json", data / "sources/law2018.json")
    local = Settings(data_dir=data, image=settings.image, docker_context=settings.docker_context)
    service = make_service(local)
    worker = Worker(service, docker)
    w = service.workspace("local", "Confinement check")
    p = service.new_plan("local", PlanCreate(workspace_id=w, title="Sandbox verification"))
    service.lock("local", p["id"], LockRequest(expected_revision=1, reviewed_fields=REQUIRED_REVIEW))
    run = service.submit(
        "local",
        RunCreate(plan_id=p["id"], limits=Limits(memory_mib=512, cpu=1, wall_seconds=30)),
        "runtime-check",
        docker.image_id(),
    )
    worker.tick()
    with service.db.transaction() as c:
        run = service.get_run(c, "local", run["id"])
    name = worker.name(run)
    try:
        info = docker.inspect(name)
        host = info["HostConfig"]
        assertions = {
            "network_none": host["NetworkMode"] == "none",
            "read_only_root": host["ReadonlyRootfs"],
            "non_root_user": info["Config"]["User"] == "1000:1000",
            "capabilities_dropped": host["CapDrop"] == ["ALL"],
            "no_new_privileges": any("no-new-privileges" in x for x in host["SecurityOpt"]),
            "memory_bound": host["Memory"] == 512 * 1024 * 1024,
            "pids_bound": host["PidsLimit"] == 96,
            "no_host_mounts": not any(x["Type"] == "bind" for x in info["Mounts"]),
            "bounded_tmpfs": "size=128m" in host["Tmpfs"]["/work"],
        }
        assert all(assertions.values()), assertions
        write = docker.command(["exec", name, "touch", "/forbidden-host-write"], check=False)
        assertions["root_write_denied"] = write.returncode != 0
        network = docker.command(
            [
                "exec",
                name,
                "Rscript",
                "-e",
                'options(timeout=2); ok <- tryCatch({readLines("https://example.com", n=1); TRUE},error=function(e) FALSE); quit(status=if(ok) 1 else 0)',
            ],
            check=False,
            timeout=10,
        )
        assertions["network_probe_denied"] = network.returncode == 0
        service.cancel("local", run["id"])
        worker.tick()
        with service.db.transaction() as c:
            result = service.get_run(c, "local", run["id"])
        assertions["cancelled_after_termination"] = (
            result["state"] == "cancelled" and docker.inspect(name) is None
        )
        assert all(assertions.values()), assertions
        receipt = {
            "date": "2026-09-11",
            "image_id": info["Image"],
            "engine_id": docker.engine_id(),
            "checks": assertions,
            "scope": "Observed curated-code confinement in the dedicated Colima VM. Not certification for hostile arbitrary code.",
        }
        (ROOT / "evidence/runtime-verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt, indent=2))
    finally:
        docker.stop(name)
        docker.remove(name)
        service.db.engine.dispose()
