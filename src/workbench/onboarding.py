"""Revisioned paper, supplement and dataset onboarding for supported adapters."""

import json
import time
from typing import Literal

from fastapi import Depends, Form, UploadFile
from fastapi.responses import Response
from pydantic import Field
from sqlalchemy import insert, select, update

from .adapters import registry
from .artifacts import digest
from .database import onboarding_revisions, onboardings, uid
from .documents import process_document
from .evidence_graph import REQUIRED_METHODS, graph, propose
from .inputs import validate_paired
from .schemas import PlanCreate, Strict
from .service import Problem


class OnboardingCreate(Strict):
    workspace_id: str
    title: str = Field(min_length=1, max_length=160)
    recipe: Literal["deseq2"] = "deseq2"


class MethodDecision(Strict):
    expected_revision: int
    key: str
    value: str | int
    origin: Literal["reported", "inferred", "manual"]
    evidence_ids: list[str] = Field(min_length=1, max_length=12)
    reason: str = Field(min_length=10, max_length=2000)


class OnboardingPlan(Strict):
    expected_revision: int
    title: str = Field(min_length=1, max_length=160)
    parameters: dict[str, str | int | float | bool] = Field(default_factory=dict)


class Onboarding:
    def __init__(self, service):
        self.service, self.db, self.store = service, service.db, service.store

    def get(self, c, actor, identity, minimum="viewer"):
        row = self.db.row(c, onboardings, identity)
        if not row:
            raise Problem(404, "Onboarding not found")
        self.service.authorize(c, row["workspace_id"], actor, minimum)
        return dict(row)

    def create(self, actor, request):
        body = {
            "title": request.title,
            "recipe": request.recipe,
            "documents": [],
            "inputs": {},
            "segments": [],
            "fields": propose([]),
            "validation": None,
            "issues": [],
        }
        identity = uid()
        with self.db.transaction() as c:
            self.service.authorize(c, request.workspace_id, actor, "editor")
            c.execute(
                insert(onboardings).values(
                    id=identity,
                    workspace_id=request.workspace_id,
                    revision=1,
                    state="draft",
                    body=body,
                    created=time.time(),
                )
            )
            self.record(c, identity, 1, body, actor)
            self.db.emit(c, request.workspace_id, "onboarding.created", actor, {"id": identity})
            return self.get(c, actor, identity)

    def record(self, c, identity, revision, body, actor):
        c.execute(
            insert(onboarding_revisions).values(
                onboarding_id=identity, revision=revision, body=body, actor=actor, created=time.time()
            )
        )

    def save(self, c, row, actor, body):
        revision = row["revision"] + 1
        changed = c.execute(
            update(onboardings)
            .where(
                onboardings.c.id == row["id"],
                onboardings.c.revision == row["revision"],
                onboardings.c.state == "draft",
            )
            .values(body=body, revision=revision)
        ).rowcount
        if changed != 1:
            raise Problem(409, "Onboarding changed or is sealed; reload before editing")
        self.record(c, row["id"], revision, body, actor)
        self.db.emit(
            c, row["workspace_id"], "onboarding.revised", actor, {"id": row["id"], "revision": revision}
        )
        return self.get(c, actor, row["id"])

    def upload(self, actor, identity, expected, role, name, kind, data):
        with self.db.transaction() as c:
            row = self.get(c, actor, identity, "editor")
            if row["revision"] != expected or row["state"] != "draft":
                raise Problem(409, "Onboarding changed or is sealed")
            if len(row["body"]["documents"]) >= 12 and role in ("paper", "supplement"):
                raise Problem(422, "At most twelve source documents are supported")
        try:
            decoded = process_document(data, kind) if role in ("paper", "supplement") else None
            if role in ("counts", "samples") and kind != "tsv":
                raise ValueError("Dataset inputs must be TSV")
            if len(data) > 9_000_000:
                raise ValueError("Input exceeds 9 MB")
            sha = self.store.put(data)
        except ValueError as error:
            raise Problem(422, str(error)) from None
        with self.db.transaction() as c:
            row = self.get(c, actor, identity, "editor")
            if row["revision"] != expected:
                raise Problem(409, "Onboarding changed while decoding; reload before uploading")
            body = json.loads(json.dumps(row["body"]))
            entry = {
                "id": uid(),
                "sha256": sha,
                "bytes": len(data),
                "name": name[:160],
                "kind": kind,
                "role": role,
            }
            if decoded:
                if any(d["sha256"] == sha for d in body["documents"]):
                    raise Problem(409, "This source document is already attached")
                body["documents"].append(entry)
                body["segments"] += [{**s, "document_id": entry["id"]} for s in decoded["segments"]]
                if len(body["segments"]) > 5000:
                    raise Problem(422, "Combined source evidence exceeds 5,000 regions")
                # New evidence may contradict a previous decision. Require renewed review.
                body["fields"] = propose(body["segments"])
                body["source_truncated"] = body.get("source_truncated", False) or decoded["truncated"]
            else:
                body["inputs"][role + ".tsv"] = entry
                body["validation"] = None
                body["issues"] = []
                body["fields"]["sample_units"]["status"] = "proposed"
            return self.save(c, row, actor, body)

    def validate(self, actor, identity, expected):
        with self.db.transaction() as c:
            row = self.get(c, actor, identity, "editor")
            if row["revision"] != expected:
                raise Problem(409, "Onboarding changed")
            body = json.loads(json.dumps(row["body"]))
            try:
                body["validation"] = validate_paired(
                    *[
                        self.store.read(body["inputs"][name]["sha256"])
                        for name in ("counts.tsv", "samples.tsv")
                    ]
                )
                body["issues"] = []
            except (KeyError, ValueError) as error:
                body["validation"] = None
                body["issues"] = [
                    str(error) if isinstance(error, ValueError) else "Attach both counts and sample metadata"
                ]
            return self.save(c, row, actor, body)

    def decide(self, actor, identity, request):
        with self.db.transaction() as c:
            row = self.get(c, actor, identity, "editor")
            if row["revision"] != request.expected_revision:
                raise Problem(409, "Onboarding changed")
            if request.key not in REQUIRED_METHODS:
                raise Problem(422, "Unknown method field")
            expected = REQUIRED_METHODS[request.key]
            if request.key == "min_total_count":
                try:
                    registry()["deseq2"].parameters["min_total_count"].validate_value(request.value)
                except ValueError as error:
                    raise Problem(422, str(error)) from None
            elif request.value != expected:
                raise Problem(422, "This value is outside the supported adapter contract")
            ids = {s["id"] for s in row["body"]["segments"]}
            if set(request.evidence_ids) - ids:
                raise Problem(422, "Unknown evidence region")
            body = json.loads(json.dumps(row["body"]))
            body["fields"][request.key].update(request.model_dump(exclude={"expected_revision", "key"}))
            body["fields"][request.key]["status"] = "accepted"
            body["fields"][request.key]["reviewed_by"] = actor
            return self.save(c, row, actor, body)

    def seal(self, actor, identity, expected):
        with self.db.transaction() as c:
            row = self.get(c, actor, identity, "editor")
            if row["revision"] != expected:
                raise Problem(409, "Onboarding changed")
            if row["state"] == "sealed":
                return row
            body = row["body"]
            if (
                not body["validation"]
                or body["issues"]
                or not any(d["role"] == "paper" for d in body["documents"])
            ):
                raise Problem(422, "Attach a paper and resolve dataset validation before sealing")
            if any(f["status"] != "accepted" for f in body["fields"].values()):
                raise Problem(422, "Resolve missing or conflicting methods and review every field")
            for entry in list(body["inputs"].values()) + body["documents"]:
                self.store.read(entry["sha256"])
            body = {**body, "evidence_graph": graph(body), "sealed_by": actor, "sealed_at": time.time()}
            body["source_sha256"] = digest({"documents": body["documents"], "fields": body["fields"]})
            body["input_hash"] = digest({name: item["sha256"] for name, item in body["inputs"].items()})
            result = self.save(c, row, actor, body)
            c.execute(update(onboardings).where(onboardings.c.id == identity).values(state="sealed"))
            return {**result, "state": "sealed"}


def register_onboarding(app, service, actor):
    onboarding = Onboarding(service)

    @app.get("/api/adapters")
    def adapters(who=Depends(actor)):
        return [a.snapshot() for a in registry().values()]

    @app.get("/api/workspaces/{identity}/onboardings")
    def list_onboardings(identity: str, who=Depends(actor)):
        with service.db.transaction() as c:
            service.authorize(c, identity, who)
            return [
                {"id": r["id"], "title": r["body"]["title"], "revision": r["revision"], "state": r["state"]}
                for r in c.execute(
                    select(onboardings)
                    .where(onboardings.c.workspace_id == identity)
                    .order_by(onboardings.c.created.desc())
                ).mappings()
            ]

    @app.post("/api/onboardings")
    def create(body: OnboardingCreate, who=Depends(actor)):
        return onboarding.create(who, body)

    @app.get("/api/onboardings/{identity}")
    def get(identity: str, who=Depends(actor)):
        with service.db.transaction() as c:
            row = onboarding.get(c, who, identity)
            history = [
                {
                    "revision": r["revision"],
                    "actor": r["actor"],
                    "created": r["created"],
                    "issues": r["body"].get("issues", []),
                    "validated": bool(r["body"].get("validation")),
                    "accepted_fields": sum(f["status"] == "accepted" for f in r["body"]["fields"].values()),
                    "input_hashes": {k: v["sha256"] for k, v in r["body"].get("inputs", {}).items()},
                }
                for r in c.execute(
                    select(onboarding_revisions)
                    .where(onboarding_revisions.c.onboarding_id == identity)
                    .order_by(onboarding_revisions.c.revision.desc())
                    .limit(200)
                ).mappings()
            ]
            return {**row, "graph": graph(row["body"]), "history": history}

    @app.post("/api/onboardings/{identity}/files")
    def upload(
        identity: str,
        file: UploadFile,
        expected_revision: int = Form(),
        role: Literal["paper", "supplement", "counts", "samples"] = Form(),
        kind: Literal["pdf", "xml", "tsv"] = Form(),
        who=Depends(actor),
    ):
        return onboarding.upload(
            who, identity, expected_revision, role, file.filename or "source", kind, file.file.read(9_000_001)
        )

    class Revision(Strict):
        expected_revision: int

    @app.post("/api/onboardings/{identity}/validate")
    def validate(identity: str, body: Revision, who=Depends(actor)):
        return onboarding.validate(who, identity, body.expected_revision)

    @app.post("/api/onboardings/{identity}/review")
    def review(identity: str, body: MethodDecision, who=Depends(actor)):
        return onboarding.decide(who, identity, body)

    @app.post("/api/onboardings/{identity}/plan")
    def create_plan(identity: str, body: OnboardingPlan, who=Depends(actor)):
        row = onboarding.seal(who, identity, body.expected_revision)
        parameters = {"min_total_count": row["body"]["fields"]["min_total_count"]["value"], **body.parameters}
        return service.new_plan(
            who,
            PlanCreate(
                workspace_id=row["workspace_id"],
                title=body.title,
                dataset_id="import_" + identity,
                recipe=row["body"]["recipe"],
                parameters=parameters,
            ),
        )

    @app.get("/api/onboardings/{identity}/documents/{document}")
    def document(identity: str, document: str, page: int | None = None, who=Depends(actor)):
        with service.db.transaction() as c:
            row = onboarding.get(c, who, identity)
        entry = next((d for d in row["body"]["documents"] if d["id"] == document), None)
        if not entry:
            raise Problem(404, "Document not found")
        data = service.store.read(entry["sha256"])
        if page is not None:
            if entry["kind"] != "pdf":
                raise Problem(422, "Only PDF documents have rendered pages")
            try:
                return Response(process_document(data, "render", page), media_type="image/png")
            except ValueError as error:
                raise Problem(422, str(error)) from None
        return Response(
            data,
            media_type={"pdf": "application/pdf", "xml": "application/xml", "tsv": "text/plain"}[
                entry["kind"]
            ],
            headers={"Content-Disposition": "attachment; filename=source." + entry["kind"]},
        )
