import json

import pytest
from sqlalchemy import func, select
from test_inputs import paired_tables

from workbench.database import runs
from workbench.schemas import LockRequest, PlanCreate
from workbench.service import REQUIRED_REVIEW, Problem
from workbench.statistics import adjust
from workbench.studies import Studies, StudyCreate


def paired_plan(service):
    counts, samples = paired_tables()
    folder = service.settings.data_dir / "datasets/airway2015"
    folder.mkdir()
    (folder / "counts.tsv").write_bytes(counts)
    (folder / "samples.tsv").write_bytes(samples)
    (service.settings.data_dir / "sources/airway2015.json").write_text(
        json.dumps({"sha256": "c" * 64, "segments": []})
    )
    workspace = service.workspace("alice", "Sensitivity")
    p = service.new_plan(
        "alice", PlanCreate(workspace_id=workspace, title="Paired", dataset_id="airway2015", recipe="deseq2")
    )
    return service.lock("alice", p["id"], LockRequest(expected_revision=1, reviewed_fields=REQUIRED_REVIEW))


def request(plan):
    return StudyCreate(
        plan_id=plan["id"],
        title="Sensitivity",
        hypothesis="Treatment response is stable across reviewed filters",
        axes={"min_total_count": [2, 10], "independent_filtering": [True, False]},
    )


def test_family_is_frozen_and_resumes_submission_without_duplicate_runs(service, monkeypatch):
    base = paired_plan(service)
    flow = Studies(service)
    study = flow.create("alice", request(base), "sha256:" + "a" * 64, "family")
    assert study["state"] == "registered" and len(study["variants"]) == 4
    assert all(v["run_id"] is None for v in study["variants"])
    assert flow.create("alice", request(base), "sha256:" + "a" * 64, "family")["id"] == study["id"]
    with service.db.transaction() as c:
        children = [service.get_plan(c, "alice", v["plan_id"]) for v in study["variants"]]
    assert all(p["body"]["input_hash"] == base["body"]["input_hash"] for p in children)
    assert all(p["state"] == "locked" for p in children)
    original = service.submit

    def interrupted(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("Process interrupted after run transaction")

    monkeypatch.setattr(service, "submit", interrupted)
    with pytest.raises(RuntimeError):
        flow.start("alice", study["id"])
    monkeypatch.setattr(service, "submit", original)
    resumed = Studies(service).start("alice", study["id"])
    assert len({v["run_id"] for v in resumed["variants"]}) == 4
    with service.db.transaction() as c:
        assert c.execute(select(func.count()).select_from(runs)).scalar() == 4
    cancelled = flow.cancel("alice", study["id"])
    assert cancelled["state"] == "cancelled"
    assert all(v["state"] == "cancelled" for v in cancelled["variants"])
    assert flow.start("alice", study["id"])["state"] == "cancelled"


def test_rejects_unregistered_axes_duplicates_and_changed_protocol(service):
    base = paired_plan(service)
    flow = Studies(service)
    flow.create("alice", request(base), "image", "same")
    with pytest.raises(Problem):
        flow.create("alice", request(base).model_copy(update={"alpha": 0.1}), "image", "same")
    for axes in ({"min_total_count": [2, 2]}, {"beta_prior": [True, False]}, {"min_total_count": [2, 99]}):
        with pytest.raises(Problem):
            flow.create("alice", request(base).model_copy(update={"axes": axes}), "image", "invalid")


def test_correction_retains_missing_hypotheses_in_family():
    assert adjust([0.01, 0.04, 0.03, 0.2]) == pytest.approx(
        [0.04, 0.05333333333333334, 0.05333333333333334, 0.2]
    )
    assert adjust([0.01], "BY", universe=4) == pytest.approx([0.08333333333333333])
    with pytest.raises(ValueError):
        adjust([0.1, 0.2], "BY", universe=1)
