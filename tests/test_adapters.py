import copy

import pytest

from workbench.adapters import Adapter, registry, resolve
from workbench.artifacts import digest
from workbench.schemas import PlanCreate
from workbench.service import Problem


def test_manifest_contract_rejects_execution_and_invalid_values():
    raw = registry()["deseq2"].model_dump()
    for field, value in [("command", "sh"), ("required_outputs", ["../result"]), ("runtime", "custom")]:
        bad = copy.deepcopy(raw)
        bad[field] = value
        with pytest.raises(ValueError):
            Adapter.model_validate(bad)
    for values in (
        {"min_total_count": True},
        {"fdr": float("nan")},
        {"script": "sh"},
        {"size_factor": "TMM"},
    ):
        with pytest.raises(ValueError):
            resolve("airway2015", "deseq2", values)
    with pytest.raises(ValueError):
        resolve("chen2016", "density")
    with pytest.raises(ValueError):
        resolve("chen2016", "mds", {"min_samples": 3})
    assert resolve("chen2016", "mds")[1]["min_samples"] == 2


def test_plan_seals_manifest_and_validates_recipe(service):
    workspace = service.workspace("alice", "Study")
    plan = service.new_plan("alice", PlanCreate(workspace_id=workspace, title="Reference"))
    snapshot = plan["body"]["adapter"].copy()
    identity = snapshot.pop("sha256")
    assert identity == digest(snapshot)
    assert plan["body"]["parameters"]["min_samples"] == 3
    with pytest.raises(Problem):
        service.new_plan("alice", PlanCreate(workspace_id=workspace, title="Bad", recipe="execute"))
