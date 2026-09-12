import hashlib
import io
import json
import tarfile
import zipfile
from pathlib import PurePosixPath

from fastapi import Depends
from fastapi.responses import Response
from sqlalchemy import select

from .artifacts import canonical
from .config import ROOT
from .database import events, reviews, revisions
from .service import Problem


def sealed_inputs(data, dataset):
    result = {}
    total = 0
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for member in archive:
            path = PurePosixPath(member.name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Unsafe sealed input path")
            if member.isdir():
                continue
            total += member.size
            if not member.isfile() or len(path.parts) != 2 or total > 30_000_000:
                raise ValueError("Unsafe sealed input archive")
            if path.parts[0] == dataset:
                name = "build/data/" + str(path)
                if name in result:
                    raise ValueError("Duplicate sealed input")
                result[name] = archive.extractfile(member).read()
    if not result:
        raise ValueError("No sealed inputs for this dataset")
    return result


def bundle(service, run):
    files = {}

    def add(name, data):
        files[name] = data

    add("run.json", canonical(run))
    add("plan.json", canonical(run["body"]["plan"]))
    add("comparison.json", canonical(run["body"].get("comparison")))
    for name, item in run["body"]["artifacts"].items():
        add("outputs/" + name, service.store.read(item["sha256"]))
    dataset = run["body"]["plan"]["dataset_id"]
    captured = run["body"]["artifacts"].get("inputs.tar")
    reproducible = bool(captured and "recipe.R" in run["body"]["artifacts"])
    if run["state"] == "succeeded" and not reproducible:
        raise Problem(409, "This older run lacks sealed input files. Execute a fresh run before exporting.")
    if captured:
        files.update(sealed_inputs(service.store.read(captured["sha256"]), dataset))
    add(
        "replay-status.json",
        canonical(
            {
                "reproducible": reproducible,
                "scope": "Sealed runtime inputs"
                if reproducible
                else "Diagnostic bundle without complete runtime inputs",
            }
        ),
    )
    for relative, name in [
        ("recipes/run.R", "build/run.R"),
        ("recipes/ADAPTATIONS.md", "ADAPTATIONS.md"),
        ("environments/Dockerfile", "build/Dockerfile"),
        ("environments/entrypoint.sh", "build/entrypoint.sh"),
        ("fixtures/law-samples.csv", "build/law-samples.csv"),
        ("environments/locked-packages.json", "locked-packages.json"),
        ("scripts/reproduce.py", "reproduce.py"),
    ]:
        add(name, (ROOT / relative).read_bytes())
    if "recipe.R" in run["body"]["artifacts"]:
        files["build/run.R"] = service.store.read(run["body"]["artifacts"]["recipe.R"]["sha256"])
    for name in ("locked-packages.json", "Dockerfile", "entrypoint.sh", "law-samples.csv"):
        if name in run["body"]["artifacts"]:
            data = service.store.read(run["body"]["artifacts"][name]["sha256"])
            files[("" if name == "locked-packages.json" else "build/") + name] = data
    files["build/locked-packages.json"] = files["locked-packages.json"]
    for suffix in ("xml", "json", "pdf"):
        path = service.settings.data_dir / f"sources/{dataset}.{suffix}"
        if path.exists():
            data = path.read_bytes()
            if suffix == "xml" and hashlib.sha256(data).hexdigest() != run["body"]["plan"]["source_sha256"]:
                raise Problem(
                    409,
                    "The source cache differs from this plan. Restore its verified source before exporting.",
                )
            add("source/" + path.name, data)
    with service.db.transaction() as c:
        rows = c.execute(select(revisions).where(revisions.c.plan_id == run["plan_id"])).mappings()
        add("plan-history.json", canonical([dict(row) for row in rows]))
        rows = c.execute(select(events).where(events.c.run_id == run["id"]).order_by(events.c.id)).mappings()
        add("run-events.json", canonical([dict(row) for row in rows]))
        rows = c.execute(select(reviews).where(reviews.c.run_id == run["id"])).mappings()
        add("reviews.json", canonical([dict(row) for row in rows]))
    add(
        "README.txt",
        b"Research Workbench result bundle\n\nRun: python3 reproduce.py --verify-only\nRerun: python3 reproduce.py --context colima-research\nRequires Python 3 and Docker. Rebuild downloads only hash-pinned R package archives.\nThe script verifies bundle hashes before execution and creates a fresh isolated container.\n\nPublic GEO counts retain source attribution and access terms. Papers are CC BY.\nSee source metadata, ADAPTATIONS.md and comparison.json for limits.\nExecution success and checked-observable agreement do not establish all conclusions of the paper.\n",
    )
    manifest = {
        "schema_version": 1,
        "run_id": run["id"],
        "files": {
            k: {"sha256": hashlib.sha256(v).hexdigest(), "bytes": len(v)} for k, v in sorted(files.items())
        },
    }
    add("manifest.json", canonical(manifest))
    result = io.BytesIO()
    with zipfile.ZipFile(result, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    return result.getvalue()


def verify_bundle(data: bytes):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or len(names) > 1000:
            raise ValueError("Duplicate or excessive archive entries")
        total = 0
        for info in z.infolist():
            p = PurePosixPath(info.filename)
            total += info.file_size
            if p.is_absolute() or ".." in p.parts or total > 100_000_000 or info.is_dir():
                raise ValueError("Unsafe archive")
        manifest = json.loads(z.read("manifest.json"))
        if set(names) != set(manifest["files"]) | {"manifest.json"}:
            raise ValueError("Unlisted or missing bundle file")
        for name, entry in manifest["files"].items():
            content = z.read(name)
            if len(content) != entry["bytes"] or hashlib.sha256(content).hexdigest() != entry["sha256"]:
                raise ValueError("Bundle integrity failure")
        return manifest


def register_exports(app, service, actor):
    @app.get("/api/runs/{identity}/export")
    def export(identity: str, who=Depends(actor)):
        with service.db.transaction() as c:
            run = service.get_run(c, who, identity)
        if run["state"] not in ("succeeded", "failed", "cancelled"):
            raise Problem(409, "Wait for a terminal execution before exporting")
        data = bundle(service, run)
        verify_bundle(data)
        with service.db.transaction() as c:
            service.db.emit(c, run["workspace_id"], "run.exported", who, {"run_id": identity}, identity)
        return Response(
            data,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="research-{identity[:8]}.zip"'},
        )
