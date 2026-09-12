"""Preregistered finite analysis families, scheduled through ordinary durable runs."""

import itertools
import json
import time

from fastapi import Depends, Header
from pydantic import Field
from sqlalchemy import insert, select, update

from .adapters import Adapter
from .artifacts import digest
from .database import plans, runs, studies, uid, variants, workspaces
from .runtime import RuntimeRegistry
from .schemas import Limits, RunCreate, Strict
from .service import Problem


class StudyCreate(Strict):
    plan_id: str
    title: str = Field(min_length=1, max_length=160)
    hypothesis: str = Field(min_length=10, max_length=2000)
    axes: dict[str, list[str | int | float | bool]] = Field(min_length=1, max_length=3)
    min_abs_log2fc: float = Field(default=1, ge=0, le=5)
    alpha: float = Field(default=0.05, ge=0.001, le=0.2)
    limits: Limits = Field(default_factory=Limits)


class Studies:
    def __init__(self, service):
        self.service, self.db = service, service.db

    def get(self, c, actor, identity, minimum="viewer"):
        row = self.db.row(c, studies, identity)
        if not row:
            raise Problem(404, "Study not found")
        self.service.authorize(c, row["workspace_id"], actor, minimum)
        entries = []
        for variant in c.execute(
            select(variants).where(variants.c.study_id == identity).order_by(variants.c.ordinal)
        ).mappings():
            run = dict(self.db.row(c, runs, variant["run_id"])) if variant["run_id"] else None
            if run:
                run["body"] = {k: v for k, v in run["body"].items() if k != "plan"}
            entries.append({**dict(variant), "state": run["state"] if run else "not_submitted", "run": run})
        return {**dict(row), "variants": entries}

    def create(self, actor, request, image_id, key):
        if not key or len(key) > 180:
            raise Problem(422, "An idempotency key of 1 to 180 characters is required")
        with self.db.transaction() as c:
            base = self.service.get_plan(c, actor, request.plan_id)
            self.service.authorize(c, base["workspace_id"], actor, "editor")
            if (
                base["state"] != "locked"
                or base["body"].get("recipe") != "deseq2"
                or not base["body"].get("inputs")
            ):
                raise Problem(
                    422, "Sensitivity studies require a locked paired DESeq2 plan with immutable inputs"
                )
            identity = digest({"workspace": base["workspace_id"], "key": key})[:32]
            c.execute(
                select(workspaces.c.id).where(workspaces.c.id == base["workspace_id"]).with_for_update()
            )
            old = self.db.row(c, studies, identity)
            if old:
                if old["body"]["request_hash"] != digest(request.model_dump()):
                    raise Problem(409, "Study idempotency key already used for another protocol")
                return self.get(c, actor, identity)
            raw = {k: v for k, v in base["body"]["adapter"].items() if k != "sha256"}
            adapter = Adapter.model_validate(raw)
            if digest(raw) != base["body"]["adapter"]["sha256"]:
                raise Problem(409, "Adapter snapshot integrity failure")
            axes = {}
            for name, values in sorted(request.axes.items()):
                rule = adapter.parameters.get(name)
                if not rule or not rule.sensitivity or not 2 <= len(values) <= 4:
                    raise Problem(422, "Axes must use two to four preregisterable adapter choices")
                if len({digest(value) for value in values}) != len(values):
                    raise Problem(422, "Duplicate sensitivity choice")
                if any(value not in rule.sensitivity for value in values):
                    raise Problem(422, "Choice is outside the reviewed sensitivity domain")
                try:
                    for value in values:
                        rule.validate_value(value)
                except ValueError as error:
                    raise Problem(422, str(error)) from None
                axes[name] = values
            size = 1
            for choices in axes.values():
                size *= len(choices)
            if not 2 <= size <= 8:
                raise Problem(422, "A study must contain two to eight variants")
            matrix = [dict(zip(axes, values, strict=True)) for values in itertools.product(*axes.values())]
            now = time.time()
            protocol = {
                "title": request.title,
                "hypothesis": request.hypothesis,
                "base_plan_id": base["id"],
                "base_plan_hash": base["body"]["plan_hash"],
                "input_hash": base["body"]["input_hash"],
                "adapter_sha256": adapter.snapshot()["sha256"],
                "image_id": image_id,
                "axes": axes,
                "matrix": matrix,
                "min_abs_log2fc": request.min_abs_log2fc,
                "alpha": request.alpha,
                "limits": request.limits.model_dump(),
                "multiplicity": "BY across every input gene and preregistered variant; missing tests count as P=1",
                "robustness_rule": "All planned variants completed, estimated in every variant, consistent sign, minimum absolute log2 fold change reached, and every family-adjusted P below alpha",
                "registered_by": actor,
                "registered_at": now,
            }
            body = {
                **protocol,
                "protocol_hash": digest(protocol),
                "request_hash": digest(request.model_dump()),
            }
            c.execute(
                insert(studies).values(
                    id=identity, workspace_id=base["workspace_id"], state="registered", body=body, created=now
                )
            )
            for ordinal, changes in enumerate(matrix, 1):
                pid = uid()
                plan_body = {
                    **base["body"],
                    "title": request.title + f" / variant {ordinal}",
                    "parent_id": base["id"],
                    "reason": "Preregistered sensitivity choices: " + json.dumps(changes, sort_keys=True),
                    "parameters": adapter.resolve({**base["body"]["parameters"], **changes}),
                    "study_id": identity,
                    "protocol_hash": body["protocol_hash"],
                    "locked_by": actor,
                    "locked_at": now,
                }
                plan_body.pop("plan_hash", None)
                plan_body["plan_hash"] = digest(plan_body)
                c.execute(
                    insert(plans).values(
                        id=pid,
                        workspace_id=base["workspace_id"],
                        revision=1,
                        state="locked",
                        body=plan_body,
                        created=now,
                    )
                )
                self.service.record_revision(c, pid, 1, plan_body, actor)
                c.execute(
                    insert(variants).values(
                        study_id=identity, ordinal=ordinal, plan_id=pid, body={"parameters": changes}
                    )
                )
            self.db.emit(
                c,
                base["workspace_id"],
                "study.preregistered",
                actor,
                {"id": identity, "protocol_hash": body["protocol_hash"], "variants": size},
            )
            return self.get(c, actor, identity)

    def start(self, actor, identity):
        with self.db.transaction() as c:
            study = self.get(c, actor, identity, "editor")
            if study["state"] == "registered":
                c.execute(update(studies).where(studies.c.id == identity).values(state="running"))
                self.db.emit(c, study["workspace_id"], "study.started", actor, {"id": identity})
        self.advance(identity)
        with self.db.transaction() as c:
            return self.get(c, actor, identity)

    def cancel(self, actor, identity):
        with self.db.transaction() as c:
            study = self.get(c, actor, identity, "editor")
            if study["state"] in ("complete", "incomplete", "cancelled"):
                return study
            c.execute(update(studies).where(studies.c.id == identity).values(state="cancel_requested"))
            self.db.emit(c, study["workspace_id"], "study.cancel_requested", actor, {"id": identity})
        self.advance(identity)
        with self.db.transaction() as c:
            return self.get(c, actor, identity)

    def advance(self, identity=None):
        with self.db.transaction() as c:
            query = select(studies).where(studies.c.state.in_(["running", "cancel_requested"]))
            if identity:
                query = query.where(studies.c.id == identity)
            pending = [dict(r) for r in c.execute(query).mappings()]
        for item in pending:
            actor = item["body"]["registered_by"]
            with self.db.transaction() as c:
                study = self.get(c, actor, item["id"])
            for variant in study["variants"]:
                if study["state"] == "cancel_requested":
                    if variant["run_id"]:
                        self.service.cancel(actor, variant["run_id"])
                    continue
                if variant["run_id"]:
                    continue
                request = RunCreate(plan_id=variant["plan_id"], limits=study["body"]["limits"])
                try:
                    run = self.service.submit(
                        actor, request, f"study:{study['id']}:{variant['ordinal']}", study["body"]["image_id"]
                    )
                except Problem as error:
                    if error.status in (409, 429):
                        break
                    raise
                with self.db.transaction() as c:
                    c.execute(
                        update(variants)
                        .where(variants.c.study_id == study["id"], variants.c.ordinal == variant["ordinal"])
                        .values(run_id=run["id"])
                    )
            with self.db.transaction() as c:
                current = self.get(c, actor, item["id"])
                states = [v["state"] for v in current["variants"]]
                active = any(s in ("queued", "running", "cancel_requested") for s in states)
                outcome = None
                if current["state"] == "cancel_requested" and not active:
                    outcome = "cancelled"
                elif not active and "not_submitted" not in states:
                    outcome = "complete" if all(s == "succeeded" for s in states) else "incomplete"
                if outcome:
                    c.execute(update(studies).where(studies.c.id == item["id"]).values(state=outcome))
                    self.db.emit(c, item["workspace_id"], "study." + outcome, actor, {"id": item["id"]})


def register_studies(app, service, actor):
    flow = Studies(service)

    @app.post("/api/studies")
    def create(body: StudyCreate, who=Depends(actor), idempotency_key: str = Header()):
        try:
            image = RuntimeRegistry(service.settings).image_id("deseq2")
        except RuntimeError as error:
            raise Problem(503, "DESeq2 runtime is not registered") from error
        return flow.create(who, body, image, idempotency_key)

    @app.get("/api/workspaces/{identity}/studies")
    def list_studies(identity: str, who=Depends(actor)):
        with service.db.transaction() as c:
            service.authorize(c, identity, who)
            return [
                dict(r)
                for r in c.execute(
                    select(studies)
                    .where(studies.c.workspace_id == identity)
                    .order_by(studies.c.created.desc())
                ).mappings()
            ]

    @app.get("/api/studies/{identity}")
    def get(identity: str, who=Depends(actor)):
        with service.db.transaction() as c:
            return flow.get(c, who, identity)

    @app.post("/api/studies/{identity}/start")
    def start(identity: str, who=Depends(actor)):
        return flow.start(who, identity)

    @app.post("/api/studies/{identity}/cancel")
    def cancel(identity: str, who=Depends(actor)):
        return flow.cancel(who, identity)
