"""Deduplicated portable family exports keep every registered outcome."""

import hashlib
import io
import zipfile

from fastapi import Depends
from fastapi.responses import Response

from .artifacts import canonical
from .config import ROOT
from .exports import bundle, verify_bundle
from .reports import render_report, report_data
from .service import Problem
from .studies import Studies


def study_bundle(service, study, actor):
    if study["state"] not in ("complete", "incomplete", "cancelled"):
        raise Problem(409, "Wait for the family to reach a terminal state before exporting")
    files, entries, completed = {}, [], []
    for variant in study["variants"]:
        entry = {
            "ordinal": variant["ordinal"],
            "state": variant["state"],
            "parameters": variant["body"]["parameters"],
            "files": {},
        }
        if variant["run_id"]:
            with service.db.transaction() as c:
                run = service.get_run(c, actor, variant["run_id"])
            data = bundle(service, run)
            verify_bundle(data)
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                for name in archive.namelist():
                    content = archive.read(name)
                    sha = hashlib.sha256(content).hexdigest()
                    files["blobs/" + sha] = content
                    entry["files"][name] = {"sha256": sha, "bytes": len(content)}
            if run["state"] == "succeeded":
                completed.append(run)
        entries.append(entry)
    files["family.json"] = canonical(
        {"schema_version": 1, "protocol": study["body"], "state": study["state"], "variants": entries}
    )
    if completed:
        # The first completed variant is the expression baseline inside a generic family export.
        data = report_data(service, study, completed[0])
        files["study.html"] = render_report(data)
    files["reproduce_study.py"] = (ROOT / "scripts/reproduce_study.py").read_bytes()
    files["README.txt"] = (
        b"Research Workbench sensitivity family\n\nOpen study.html for the offline explorer.\nVerify: python3 reproduce_study.py --verify-only\nReplay one: python3 reproduce_study.py --variant 1 --context colima-research\nReplay all completed variants: python3 reproduce_study.py --context colima-research\n\nPython 3 and Docker are required for replay. Numerical outputs, source documents and runtime files are deduplicated by SHA-256 under blobs/. Every planned outcome is listed in family.json. Reruns use the original per-run resource limits.\n"
    )
    files["manifest.json"] = canonical(
        {
            "schema_version": 2,
            "study_id": study["id"],
            "files": {
                name: {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}
                for name, content in sorted(files.items())
            },
        }
    )
    result = io.BytesIO()
    with zipfile.ZipFile(result, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    data = result.getvalue()
    verify_bundle(data, max_bytes=512_000_000)
    return data


def register_study_exports(app, service, actor):
    @app.get("/api/studies/{identity}/export")
    def export(identity: str, who=Depends(actor)):
        with service.db.transaction() as c:
            study = Studies(service).get(c, who, identity)
        data = study_bundle(service, study, who)
        return Response(
            data,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="study-{identity[:8]}.zip"'},
        )
