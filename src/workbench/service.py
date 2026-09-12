import json
import time

from sqlalchemy import func, insert, select, update

from .adapters import resolve
from .artifacts import digest
from .database import Database, members, plans, revisions, runs, uid, workspaces
from .fixtures import SOURCES
from .schemas import Correction, LockRequest, PlanCreate, RunCreate

REQUIRED_REVIEW = ["dataset", "samples", "filter", "environment", "comparison"]
ROLES = {"owner": 4, "editor": 3, "reviewer": 2, "viewer": 1}


class Problem(Exception):
    def __init__(self, status: int, message: str):
        self.status, self.message = status, message


class Service:
    def __init__(self, db: Database, settings, store):
        self.db, self.settings, self.store = db, settings, store

    def authorize(self, c, workspace_id, actor, minimum="viewer"):
        role = c.execute(
            select(members.c.role).where(members.c.workspace_id == workspace_id, members.c.subject == actor)
        ).scalar()
        if not role or ROLES[role] < ROLES[minimum]:
            raise Problem(403, "Workspace access denied")
        return role

    def workspace(self, actor, name):
        with self.db.transaction() as c:
            identity = uid()
            c.execute(insert(workspaces).values(id=identity, name=name, created=time.time()))
            c.execute(insert(members).values(workspace_id=identity, subject=actor, role="owner"))
            self.db.emit(c, identity, "workspace.created", actor, {"name": name})
            return identity

    def source(self, dataset):
        path = self.settings.data_dir / f"sources/{dataset}.json"
        if dataset not in SOURCES or not path.exists():
            raise Problem(409, "Source is unavailable. Run workbench setup first.")
        return json.loads(path.read_text())

    def new_plan(self, actor, request: PlanCreate):
        source = self.source(request.dataset_id)
        body = request.model_dump()
        try:
            adapter, body["parameters"] = resolve(request.dataset_id, request.recipe, request.parameters)
        except ValueError as error:
            raise Problem(422, str(error)) from None
        body["adapter"] = adapter.snapshot()
        body["source_sha256"] = source["sha256"]
        body["environment"] = adapter.environment
        body["adaptations"] = adapter.adaptations
        body["reviewed_fields"] = []
        with self.db.transaction() as c:
            self.authorize(c, request.workspace_id, actor, "editor")
            if request.parent_id:
                parent = self.get_plan(c, actor, request.parent_id)
                if (
                    parent["workspace_id"] != request.workspace_id
                    or parent["body"]["dataset_id"] != request.dataset_id
                ):
                    raise Problem(422, "Variation must use the same workspace and dataset as its parent")
                if parent["state"] != "locked" or not request.reason.strip():
                    raise Problem(422, "A variation needs a locked parent and a reason")
            identity = uid()
            c.execute(
                insert(plans).values(
                    id=identity,
                    workspace_id=request.workspace_id,
                    revision=1,
                    state="draft",
                    body=body,
                    created=time.time(),
                )
            )
            self.record_revision(c, identity, 1, body, actor)
            self.db.emit(c, request.workspace_id, "plan.created", actor, {"plan_id": identity})
            return self.get_plan(c, actor, identity)

    def get_plan(self, c, actor, identity):
        row = self.db.row(c, plans, identity)
        if not row:
            raise Problem(404, "Plan not found")
        self.authorize(c, row["workspace_id"], actor)
        return dict(row)

    def record_revision(self, c, identity, revision, body, actor):
        c.execute(
            insert(revisions).values(
                plan_id=identity, revision=revision, body=body, actor=actor, created=time.time()
            )
        )

    def correct(self, actor, identity, request: Correction):
        with self.db.transaction() as c:
            plan = self.get_plan(c, actor, identity)
            self.authorize(c, plan["workspace_id"], actor, "editor")
            if plan["revision"] != request.expected_revision or plan["state"] != "draft":
                raise Problem(409, "Plan changed or is locked. Reload before editing.")
            try:
                _, parameters = resolve(
                    plan["body"]["dataset_id"], plan["body"]["recipe"], request.parameters
                )
            except ValueError as error:
                raise Problem(422, str(error)) from None
            valid_ids = {e["id"] for e in self.source(plan["body"]["dataset_id"])["segments"]}
            if set(request.evidence_ids) - valid_ids:
                raise Problem(422, "Unknown source evidence")
            body = {
                **plan["body"],
                "parameters": parameters,
                "reason": request.reason,
                "evidence_ids": request.evidence_ids,
                "reviewed_fields": [],
            }
            revision = plan["revision"] + 1
            changed = c.execute(
                update(plans)
                .where(
                    plans.c.id == identity,
                    plans.c.revision == request.expected_revision,
                    plans.c.state == "draft",
                )
                .values(revision=revision, body=body)
            ).rowcount
            if changed != 1:
                raise Problem(409, "Concurrent plan update")
            self.record_revision(c, identity, revision, body, actor)
            self.db.emit(
                c,
                plan["workspace_id"],
                "plan.corrected",
                actor,
                {"plan_id": identity, "revision": revision, "reason": request.reason},
            )
            return self.get_plan(c, actor, identity)

    def lock(self, actor, identity, request: LockRequest):
        with self.db.transaction() as c:
            plan = self.get_plan(c, actor, identity)
            self.authorize(c, plan["workspace_id"], actor, "editor")
            if plan["revision"] != request.expected_revision or plan["state"] != "draft":
                raise Problem(409, "Plan changed or is already locked")
            if set(request.reviewed_fields) != set(REQUIRED_REVIEW):
                raise Problem(
                    422, "Review dataset, samples, filter, environment and comparison before locking"
                )
            body = {
                **plan["body"],
                "reviewed_fields": REQUIRED_REVIEW,
                "locked_by": actor,
                "locked_at": time.time(),
            }
            body["plan_hash"] = digest(body)
            changed = c.execute(
                update(plans)
                .where(
                    plans.c.id == identity,
                    plans.c.revision == request.expected_revision,
                    plans.c.state == "draft",
                )
                .values(state="locked", body=body, revision=plan["revision"] + 1)
            ).rowcount
            if changed != 1:
                raise Problem(409, "Concurrent plan update")
            self.record_revision(c, identity, plan["revision"] + 1, body, actor)
            self.db.emit(
                c,
                plan["workspace_id"],
                "plan.locked",
                actor,
                {"plan_id": identity, "hash": body["plan_hash"]},
            )
            return self.get_plan(c, actor, identity)

    def submit(self, actor, request: RunCreate, key: str, image_id: str):
        with self.db.transaction() as c:
            plan = self.get_plan(c, actor, request.plan_id)
            self.authorize(c, plan["workspace_id"], actor, "editor")
            if plan["state"] != "locked":
                raise Problem(409, "Lock the reviewed plan before running")
            if not key or len(key) > 200:
                raise Problem(422, "An idempotency key of 1 to 200 characters is required")
            req_hash = digest(request.model_dump())
            # Serialize same-workspace submissions on PostgreSQL, including quota/idempotency checks.
            c.execute(
                select(workspaces.c.id).where(workspaces.c.id == plan["workspace_id"]).with_for_update()
            )
            existing = (
                c.execute(select(runs).where(runs.c.workspace_id == plan["workspace_id"], runs.c.key == key))
                .mappings()
                .first()
            )
            if existing:
                if existing["request_hash"] != req_hash:
                    raise Problem(409, "Idempotency key already used for a different request")
                return dict(existing)
            pending = c.execute(
                select(func.count())
                .select_from(runs)
                .where(
                    runs.c.workspace_id == plan["workspace_id"],
                    runs.c.state.in_(["queued", "running", "cancel_requested"]),
                )
            ).scalar()
            if pending >= 8:
                raise Problem(429, "Workspace queue limit reached")
            identity, now = uid(), time.time()
            cache_key = digest(
                {"plan": plan["body"], "image": image_id, "limits": request.limits.model_dump()}
            )
            body = {
                "plan": plan["body"],
                "limits": request.limits.model_dump(),
                "image_id": image_id,
                "cache_key": cache_key,
                "artifacts": {},
                "comparison": None,
                "submitted_by": actor,
            }
            state = "queued"
            if request.use_cache:
                for previous in c.execute(
                    select(runs)
                    .where(runs.c.workspace_id == plan["workspace_id"], runs.c.state == "succeeded")
                    .order_by(runs.c.created.desc())
                ).mappings():
                    if previous["body"]["cache_key"] == cache_key:
                        for artifact in previous["body"]["artifacts"].values():
                            self.store.read(artifact["sha256"])
                        body.update({k: previous["body"][k] for k in ("artifacts", "comparison")})
                        body["cached_from"] = previous["id"]
                        state = "succeeded"
                        break
            c.execute(
                insert(runs).values(
                    id=identity,
                    workspace_id=plan["workspace_id"],
                    plan_id=plan["id"],
                    key=key,
                    request_hash=req_hash,
                    state=state,
                    epoch=0,
                    lease_until=0,
                    cancel_requested=0,
                    body=body,
                    created=now,
                    updated=now,
                )
            )
            self.db.emit(
                c,
                plan["workspace_id"],
                "run.cached" if state == "succeeded" else "run.queued",
                actor,
                {"run_id": identity},
                identity,
            )
            return dict(self.db.row(c, runs, identity))

    def get_run(self, c, actor, identity):
        row = self.db.row(c, runs, identity)
        if not row:
            raise Problem(404, "Run not found")
        self.authorize(c, row["workspace_id"], actor)
        return dict(row)

    def cancel(self, actor, identity):
        with self.db.transaction() as c:
            run = self.get_run(c, actor, identity)
            self.authorize(c, run["workspace_id"], actor, "editor")
            if run["state"] not in ("queued", "running", "cancel_requested"):
                return run
            state = "cancelled" if run["state"] == "queued" else "cancel_requested"
            c.execute(
                update(runs)
                .where(runs.c.id == identity)
                .values(cancel_requested=1, state=state, updated=time.time())
            )
            self.db.emit(c, run["workspace_id"], "run." + state, actor, {}, identity)
            return dict(self.db.row(c, runs, identity))
