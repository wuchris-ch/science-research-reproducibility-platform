from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select

from workbench.database import revisions
from workbench.schemas import Correction, LockRequest, Parameters, PlanCreate, RunCreate
from workbench.service import REQUIRED_REVIEW, Problem


def locked(service):
    w = service.workspace("alice", "Lab")
    p = service.new_plan("alice", PlanCreate(workspace_id=w, title="Density"))
    return service.lock("alice", p["id"], LockRequest(expected_revision=1, reviewed_fields=REQUIRED_REVIEW))


def test_revisions_and_lock(service):
    w = service.workspace("alice", "Lab")
    p = service.new_plan("alice", PlanCreate(workspace_id=w, title="Density"))
    patch = Correction(
        expected_revision=1,
        parameters=Parameters(filter_policy="cpm1"),
        reason="Check robustness",
        evidence_ids=["law2018:0"],
    )
    changed = service.correct("alice", p["id"], patch)
    assert changed["revision"] == 2
    with pytest.raises(Problem) as e:
        service.correct("alice", p["id"], patch)
    assert e.value.status == 409
    with pytest.raises(Problem):
        service.lock("alice", p["id"], LockRequest(expected_revision=2, reviewed_fields=["dataset"]))
    service.lock("alice", p["id"], LockRequest(expected_revision=2, reviewed_fields=REQUIRED_REVIEW))
    with pytest.raises(Problem):
        service.correct("alice", p["id"], patch.model_copy(update={"expected_revision": 3}))
    with service.db.transaction() as c:
        history = c.execute(select(revisions).where(revisions.c.plan_id == p["id"])).mappings().all()
    assert len(history) == 3
    assert history[0]["body"]["parameters"]["filter_policy"] == "published"


def test_concurrent_idempotency_and_scope(service):
    p = locked(service)
    request = RunCreate(plan_id=p["id"])
    with ThreadPoolExecutor(max_workers=4) as pool:
        result = list(pool.map(lambda _: service.submit("alice", request, "one", "sha256:abc"), range(4)))
    assert len({r["id"] for r in result}) == 1
    with pytest.raises(Problem) as e:
        service.submit("alice", request.model_copy(update={"use_cache": True}), "one", "sha256:abc")
    assert e.value.status == 409
    with service.db.transaction() as c, pytest.raises(Problem):
        service.get_run(c, "bob", result[0]["id"])


def test_injected_evidence_cannot_correct_plan(service):
    p = locked(service)
    w = service.workspace("alice", "Other")
    draft = service.new_plan("alice", PlanCreate(workspace_id=w, title="Draft"))
    with pytest.raises(Problem):
        service.correct(
            "alice",
            draft["id"],
            Correction(
                expected_revision=1, parameters=Parameters(), reason="New claim", evidence_ids=["invented"]
            ),
        )
    with pytest.raises(Problem):
        service.new_plan(
            "alice", PlanCreate(workspace_id=w, title="Variation", parent_id=p["id"], reason="test")
        )
