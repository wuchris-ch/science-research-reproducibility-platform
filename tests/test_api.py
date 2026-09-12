import pytest
from fastapi.testclient import TestClient

from workbench.api import create_app
from workbench.service import REQUIRED_REVIEW


class Runtime:
    def image_id(self):
        return "image"


@pytest.fixture
def client(service):
    service.settings.origins = ["http://testserver"]
    app = create_app(service.settings, Runtime())
    with TestClient(app) as c:
        token = c.get("/api/session").json()["csrf"]
        c.headers["x-csrf-token"] = token
        yield c


def test_api_review_run_export_boundaries(client):
    w = client.post("/api/workspaces", json={"name": "Lab"}).json()["id"]
    p = client.post("/api/plans", json={"workspace_id": w, "title": "Figure 1"}).json()
    assert (
        client.post("/api/runs", json={"plan_id": p["id"]}, headers={"Idempotency-Key": "x"}).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/plans/{p['id']}/lock", json={"expected_revision": 1, "reviewed_fields": REQUIRED_REVIEW}
        ).status_code
        == 200
    )
    r = client.post("/api/runs", json={"plan_id": p["id"]}, headers={"Idempotency-Key": "x"}).json()
    assert r["state"] == "queued"
    assert client.get(f"/api/runs/{r['id']}/export").status_code == 409
    assert client.post(f"/api/runs/{r['id']}/cancel").json()["state"] == "cancelled"
    assert client.get(f"/api/workspaces/{w}/events").json()[-1]["kind"] == "run.cancelled"


def test_csrf_host_and_origin(client):
    assert (
        client.post("/api/workspaces", json={"name": "Lab"}, headers={"x-csrf-token": ""}).status_code == 403
    )
    assert client.get("/api/session", headers={"origin": "https://evil.example"}).status_code == 403
    assert client.get("/api/session", headers={"host": "attacker.example"}).status_code == 403
    assert client.get("/api/workspaces", headers={"sec-fetch-site": "cross-site"}).status_code == 403


def test_last_owner_and_source_validation(client):
    w = client.post("/api/workspaces", json={"name": "Lab"}).json()["id"]
    assert (
        client.put(f"/api/workspaces/{w}/members", json={"subject": "local", "role": "viewer"}).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/workspaces/{w}/sources", files={"file": ("x.html", b"<script>alert(1)</script>")}
        ).status_code
        == 422
    )
    assert client.get("/api/workspaces/unknown").status_code == 403


def test_session_reuse_does_not_invalidate_another_tab(client):
    first = client.get("/api/session").json()["csrf"]
    second = client.get("/api/session").json()["csrf"]
    assert first == second
    assert (
        client.post(
            "/api/workspaces", json={"name": "Another tab"}, headers={"x-csrf-token": first}
        ).status_code
        == 200
    )


def test_gene_explorer_paginates_missing_values_and_rechecks_access_after_cache(client):
    from sqlalchemy import delete, update

    from workbench.database import members, runs

    w = client.post("/api/workspaces", json={"name": "Gene results"}).json()["id"]
    p = client.post("/api/plans", json={"workspace_id": w, "title": "Gene effects"}).json()
    client.post(
        f"/api/plans/{p['id']}/lock", json={"expected_revision": 1, "reviewed_fields": REQUIRED_REVIEW}
    )
    run = client.post("/api/runs", json={"plan_id": p["id"]}, headers={"Idempotency-Key": "genes"}).json()
    service = client.app.state.service
    files = {
        "effects.tsv": b"gene_id\tlog2FoldChange\tpvalue\tpadj\tstatus\ng2\tNA\tNA\tNA\tprefiltered\ng1\t2\t0.01\t0.02\ttested\n",
        "normalized-counts.tsv": b"gene_id\ts1\ts2\ng1\t10\t40\ng2\t0\t0\n",
        "samples.tsv": b"sample\tdonor\tgroup\ns1\td1\tcontrol\ns2\td1\ttreated\n",
    }
    run["body"]["artifacts"] = {
        name: {"sha256": service.store.put(data), "bytes": len(data)} for name, data in files.items()
    }
    with service.db.transaction() as c:
        c.execute(update(runs).where(runs.c.id == run["id"]).values(state="succeeded", body=run["body"]))
    route = f"/api/runs/{run['id']}/genes"
    result = client.get(route, params={"limit": 1}).json()
    assert result["total"] == 2 and result["rows"][0]["gene_id"] == "g1"
    assert client.get(route, params={"offset": 1}).json()["rows"][0]["padj"] is None
    detail = client.get(route + "/g1").json()
    assert [s["normalized_count"] for s in detail["samples"]] == [10, 40]
    assert detail["effects_sha256"] == run["body"]["artifacts"]["effects.tsv"]["sha256"]
    assert client.get(route + "/absent").status_code == 404
    with service.db.transaction() as c:
        c.execute(delete(members).where(members.c.workspace_id == w))
    assert client.get(route).status_code == 403
    assert client.get(route + "/g1").status_code == 403


def test_review_survives_workspace_poll(client):
    from sqlalchemy import update

    from workbench.database import runs

    w = client.post("/api/workspaces", json={"name": "Review lab"}).json()["id"]
    p = client.post("/api/plans", json={"workspace_id": w, "title": "Figure"}).json()
    client.post(
        "/api/plans/" + p["id"] + "/lock", json={"expected_revision": 1, "reviewed_fields": REQUIRED_REVIEW}
    )
    r = client.post("/api/runs", json={"plan_id": p["id"]}, headers={"Idempotency-Key": "review"}).json()
    with client.app.state.service.db.transaction() as c:
        c.execute(update(runs).where(runs.c.id == r["id"]).values(state="succeeded"))
    assert (
        client.post(
            "/api/runs/" + r["id"] + "/reviews",
            json={"status": "disputed", "note": "A documented discrepancy"},
        ).status_code
        == 200
    )
    assert client.get("/api/workspaces/" + w).json()["runs"][0]["reviews"][0]["body"]["status"] == "disputed"


def test_imported_pdfs_are_scoped_and_downloaded_as_inert_attachments(client):
    w = client.post("/api/workspaces", json={"name": "Sources"}).json()["id"]
    other = client.post("/api/workspaces", json={"name": "Other sources"}).json()["id"]
    data = b"%PDF-1.7\nUnreviewed input bytes for inert storage testing."
    source = client.post(
        f"/api/workspaces/{w}/sources", files={"file": ("paper.pdf", data, "application/pdf")}
    ).json()
    assert source["executable"] is False and source["status"] == "unreviewed"
    assert len(client.get(f"/api/workspaces/{w}/sources").json()) == 1
    assert client.get(f"/api/workspaces/{other}/sources/{source['id']}/download").status_code == 404
    response = client.get(f"/api/workspaces/{w}/sources/{source['id']}/download")
    assert response.content == data
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["content-disposition"].startswith("attachment;")


def test_health_reports_database_failure(client, monkeypatch):
    from sqlalchemy.exc import OperationalError

    def unavailable():
        raise OperationalError("SELECT 1", {}, Exception("database offline"))

    assert client.get("/api/health").status_code == 200
    monkeypatch.setattr(client.app.state.service.db.engine, "connect", unavailable)
    response = client.get("/api/health")
    assert response.status_code == 503
    assert response.json()["database"] == "unreachable"
