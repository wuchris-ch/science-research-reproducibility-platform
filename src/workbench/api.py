import asyncio
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field
from sqlalchemy import func, insert, select, text, update
from sqlalchemy.exc import SQLAlchemyError

from .artifacts import ArtifactStore
from .auth import Auth
from .comparison import compare_fresh
from .config import ROOT, Settings
from .database import Database, attachments, events, members, plans, reviews, revisions, runs, uid, workspaces
from .fixtures import SOURCES
from .request_limits import RequestLimit
from .runtime import RuntimeRegistry
from .schemas import Correction, LockRequest, Membership, PlanCreate, Review, RunCreate, Strict
from .service import Problem, Service


class WorkspaceCreate(Strict):
    name: str = Field(min_length=1, max_length=120)


class Note(Strict):
    text: str = Field(min_length=1, max_length=4000)


class CompareRequest(Strict):
    other_run_id: str


def create_app(settings=None, docker=None):
    settings = settings or Settings()
    settings.initialize()
    db = Database(settings.database_url)
    db.migrate()
    store = ArtifactStore(settings.data_dir / "blobs")
    service = Service(db, settings, store)
    docker = docker or RuntimeRegistry(settings)
    auth = Auth(settings)

    @asynccontextmanager
    async def lifespan(app):
        yield
        db.engine.dispose()

    app = FastAPI(title="Research Workbench", version="0.1.0", lifespan=lifespan)
    app.state.service = service
    app.state.auth = auth
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-CSRF-Token", "Idempotency-Key", "Last-Event-ID"],
    )
    app.add_middleware(RequestLimit, max_bytes=10_000_000)

    @app.exception_handler(Problem)
    async def problem(_, error):
        return JSONResponse({"detail": error.message}, status_code=error.status)

    @app.middleware("http")
    async def boundary(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self' blob:; frame-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'"
        )
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    actor = auth.actor

    @app.get("/api/health")
    def health():
        try:
            with db.engine.connect() as c:
                c.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return JSONResponse({"status": "unavailable", "database": "unreachable"}, status_code=503)
        return {"status": "ok", "version": "0.1.0", "identity_mode": "oidc" if auth.jwks else "local"}

    @app.get("/api/session")
    def session(request: Request):
        token, csrf = auth.session(request)
        response = JSONResponse({"subject": "local", "csrf": csrf, "mode": "local"})
        response.set_cookie(
            "research_session",
            token,
            httponly=True,
            samesite="strict",
            secure=request.url.scheme == "https",
            max_age=86400,
        )
        return response

    @app.get("/api/me")
    def me(who=Depends(actor)):
        return {"subject": who, "mode": "oidc" if auth.jwks else "local"}

    @app.get("/api/workspaces")
    def list_workspaces(who=Depends(actor)):
        with db.transaction() as c:
            return [
                dict(r)
                for r in c.execute(
                    select(workspaces, members.c.role).join(members).where(members.c.subject == who)
                ).mappings()
            ]

    @app.post("/api/workspaces")
    def new_workspace(body: WorkspaceCreate, who=Depends(actor)):
        return {"id": service.workspace(who, body.name)}

    @app.get("/api/workspaces/{identity}")
    def workspace(identity: str, who=Depends(actor)):
        with db.transaction() as c:
            role = service.authorize(c, identity, who)
            recent = [
                dict(r)
                for r in c.execute(
                    select(runs)
                    .where(runs.c.workspace_id == identity)
                    .order_by(runs.c.created.desc())
                    .limit(200)
                ).mappings()
            ]
            by_run = {r["id"]: r for r in recent}
            for run in recent:
                run["reviews"] = []
            if by_run:
                for row in c.execute(
                    select(reviews).where(reviews.c.run_id.in_(by_run)).order_by(reviews.c.created)
                ).mappings():
                    by_run[row["run_id"]]["reviews"].append(dict(row))
            return {
                "workspace": dict(db.row(c, workspaces, identity)),
                "role": role,
                "plans": [
                    dict(r)
                    for r in c.execute(
                        select(plans).where(plans.c.workspace_id == identity).order_by(plans.c.created.desc())
                    ).mappings()
                ],
                "runs": recent,
            }

    @app.get("/api/workspaces/{identity}/members")
    def membership(identity: str, who=Depends(actor)):
        with db.transaction() as c:
            service.authorize(c, identity, who)
            return [
                dict(r)
                for r in c.execute(select(members).where(members.c.workspace_id == identity)).mappings()
            ]

    @app.put("/api/workspaces/{identity}/members")
    def member(identity: str, body: Membership, who=Depends(actor)):
        with db.transaction() as c:
            service.authorize(c, identity, who, "owner")
            c.execute(select(workspaces.c.id).where(workspaces.c.id == identity).with_for_update())
            previous = c.execute(
                select(members.c.role).where(
                    members.c.workspace_id == identity, members.c.subject == body.subject
                )
            ).scalar()
            if previous == "owner" and body.role != "owner":
                owners = c.execute(
                    select(func.count())
                    .select_from(members)
                    .where(members.c.workspace_id == identity, members.c.role == "owner")
                ).scalar()
                if owners <= 1:
                    raise Problem(409, "Workspace must retain an owner")
            if previous:
                c.execute(
                    update(members)
                    .where(members.c.workspace_id == identity, members.c.subject == body.subject)
                    .values(role=body.role)
                )
            else:
                c.execute(insert(members).values(workspace_id=identity, **body.model_dump()))
            db.emit(c, identity, "membership.changed", who, body.model_dump())
        return {"ok": True}

    @app.get("/api/sources")
    def sources(who=Depends(actor)):
        return [{"id": k, **v} for k, v in SOURCES.items()]

    @app.get("/api/sources/{identity}")
    def source(identity: str, who=Depends(actor)):
        return service.source(identity, who)

    @app.get("/api/sources/{identity}/asset/{kind}")
    def source_asset(identity: str, kind: str, who=Depends(actor)):
        allowed = {
            "pdf": f"{identity}.pdf",
            "figure": f"{identity}-figure.gif",
            "xml": f"{identity}.xml",
            "page": f"{identity}-page.png",
        }
        if identity not in SOURCES or kind not in allowed:
            raise Problem(404, "Source asset not found")
        path = settings.data_dir / "sources" / allowed[kind]
        if not path.exists():
            raise Problem(404, "Source asset unavailable")
        return FileResponse(
            path,
            media_type={
                "pdf": "application/pdf",
                "figure": "image/gif",
                "xml": "application/xml",
                "page": "image/png",
            }[kind],
        )

    @app.post("/api/plans")
    def new_plan(body: PlanCreate, who=Depends(actor)):
        return service.new_plan(who, body)

    @app.get("/api/plans/{identity}")
    def get_plan(identity: str, who=Depends(actor)):
        with db.transaction() as c:
            p = service.get_plan(c, who, identity)
            p["history"] = [
                dict(r)
                for r in c.execute(
                    select(revisions).where(revisions.c.plan_id == identity).order_by(revisions.c.revision)
                ).mappings()
            ]
            return p

    @app.post("/api/plans/{identity}/correct")
    def correct(identity: str, body: Correction, who=Depends(actor)):
        return service.correct(who, identity, body)

    @app.post("/api/plans/{identity}/lock")
    def lock(identity: str, body: LockRequest, who=Depends(actor)):
        return service.lock(who, identity, body)

    @app.post("/api/runs")
    def submit(body: RunCreate, who=Depends(actor), idempotency_key: str = Header()):
        try:
            with db.transaction() as c:
                plan = service.get_plan(c, who, body.plan_id)
            profile = plan["body"].get("adapter", {}).get("runtime", "historical")
            image = docker.image_id(profile) if isinstance(docker, RuntimeRegistry) else docker.image_id()
        except (RuntimeError, OSError) as e:
            raise Problem(503, "Scientific runtime unavailable. Run workbench doctor.") from e
        return service.submit(who, body, idempotency_key, image)

    @app.get("/api/runs/{identity}")
    def run(identity: str, who=Depends(actor)):
        with db.transaction() as c:
            r = service.get_run(c, who, identity)
            r["reviews"] = [
                dict(x)
                for x in c.execute(
                    select(reviews).where(reviews.c.run_id == identity).order_by(reviews.c.created)
                ).mappings()
            ]
            return r

    @app.post("/api/runs/{identity}/cancel")
    def cancel(identity: str, who=Depends(actor)):
        return service.cancel(who, identity)

    @app.get("/api/runs/{identity}/artifacts/{name:path}")
    def artifact(identity: str, name: str, who=Depends(actor)):
        with db.transaction() as c:
            r = service.get_run(c, who, identity)
        item = r["body"].get("artifacts", {}).get(name)
        if not item:
            raise Problem(404, "Artifact not found")
        try:
            data = store.read(item["sha256"])
        except (OSError, ValueError):
            raise Problem(409, "Artifact failed integrity verification") from None
        media = {
            "png": "image/png",
            "json": "application/json",
            "tsv": "text/tab-separated-values",
            "log": "text/plain",
            "txt": "text/plain",
        }.get(name.rsplit(".", 1)[-1], "application/octet-stream")
        return Response(
            data,
            media_type=media,
            headers={"ETag": item["sha256"], "Content-Disposition": f'inline; filename="{Path(name).name}"'},
        )

    @app.post("/api/runs/{identity}/compare")
    def fresh_compare(identity: str, body: CompareRequest, who=Depends(actor)):
        with db.transaction() as c:
            left = service.get_run(c, who, identity)
            right = service.get_run(c, who, body.other_run_id)
        if left["workspace_id"] != right["workspace_id"]:
            raise Problem(422, "Compare runs in the same workspace")
        return compare_fresh(store, left["body"]["artifacts"], right["body"]["artifacts"])

    @app.post("/api/runs/{identity}/reviews")
    def review(identity: str, body: Review, who=Depends(actor)):
        with db.transaction() as c:
            run = service.get_run(c, who, identity)
            service.authorize(c, run["workspace_id"], who, "reviewer")
            if run["state"] != "succeeded":
                raise Problem(409, "Review a completed execution")
            c.execute(
                insert(reviews).values(
                    id=uid(), run_id=identity, actor=who, body=body.model_dump(), created=time.time()
                )
            )
            db.emit(c, run["workspace_id"], "review.recorded", who, body.model_dump(), identity)
        return {"ok": True}

    @app.post("/api/runs/{identity}/notes")
    def note(identity: str, body: Note, who=Depends(actor)):
        with db.transaction() as c:
            run = service.get_run(c, who, identity)
            service.authorize(c, run["workspace_id"], who, "reviewer")
            db.emit(c, run["workspace_id"], "note.added", who, body.model_dump(), identity)
        return {"ok": True}

    @app.get("/api/workspaces/{identity}/events")
    def history(identity: str, after: int = 0, who=Depends(actor)):
        with db.transaction() as c:
            service.authorize(c, identity, who)
            return [
                dict(r)
                for r in c.execute(
                    select(events)
                    .where(events.c.workspace_id == identity, events.c.id > after)
                    .order_by(events.c.id)
                    .limit(500)
                ).mappings()
            ]

    @app.get("/api/workspaces/{identity}/stream")
    async def stream(identity: str, request: Request, after: int = 0, who=Depends(actor)):
        with db.transaction() as c:
            service.authorize(c, identity, who)
        cursor = max(after, int(request.headers.get("last-event-id", "0")))

        async def feed():
            nonlocal cursor
            for _ in range(60):
                if await request.is_disconnected():
                    break
                rows = history(identity, cursor, who)
                for row in rows:
                    cursor = row["id"]
                    yield f"id: {cursor}\nevent: update\ndata: {json.dumps(row)}\n\n"
                if not rows:
                    yield ": heartbeat\n\n"
                await asyncio.sleep(1)

        return StreamingResponse(feed(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})

    @app.post("/api/workspaces/{identity}/sources")
    async def upload(identity: str, file: UploadFile, who=Depends(actor)):
        with db.transaction() as c:
            service.authorize(c, identity, who, "editor")
        data = await file.read(10_000_001)
        if len(data) > 10_000_000:
            raise Problem(413, "Source upload exceeds 10 MB")
        if not data.startswith(b"%PDF"):
            raise Problem(422, "Upload a PDF. Imported sources remain unreviewed and cannot execute.")
        # Store inert bytes and serve only as an attachment. Parsing needs a separately bounded process.
        item = {
            "name": (file.filename or "paper.pdf")[:200],
            "sha256": store.put(data),
            "bytes": len(data),
            "status": "unreviewed",
            "executable": False,
        }
        with db.transaction() as c:
            service.authorize(c, identity, who, "editor")
            identity_source = uid()
            c.execute(
                insert(attachments).values(
                    id=identity_source, workspace_id=identity, body=item, created=time.time()
                )
            )
            db.emit(
                c, identity, "source.uploaded", who, {"source_id": identity_source, "sha256": item["sha256"]}
            )
        return {"id": identity_source, **item}

    @app.get("/api/workspaces/{identity}/sources")
    def imported_sources(identity: str, who=Depends(actor)):
        with db.transaction() as c:
            service.authorize(c, identity, who)
            return [
                dict(row)
                for row in c.execute(
                    select(attachments)
                    .where(attachments.c.workspace_id == identity)
                    .order_by(attachments.c.created.desc())
                    .limit(200)
                ).mappings()
            ]

    @app.get("/api/workspaces/{identity}/sources/{source_id}/download")
    def imported_source(identity: str, source_id: str, who=Depends(actor)):
        with db.transaction() as c:
            service.authorize(c, identity, who)
            row = db.row(c, attachments, source_id)
            if not row or row["workspace_id"] != identity:
                raise Problem(404, "Imported source not found")
            data = store.read(row["body"]["sha256"])
        return Response(
            data,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="source-{source_id[:8]}.pdf"'},
        )

    # Optional routes registered separately to keep core execution independent of inference.
    from .exports import register_exports

    register_exports(app, service, actor)
    from .extraction import register_extraction

    register_extraction(app, service, actor)
    from .onboarding import register_onboarding

    register_onboarding(app, service, actor)
    from .studies import register_studies

    register_studies(app, service, actor)
    dist = ROOT / "web/dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")
    return app
