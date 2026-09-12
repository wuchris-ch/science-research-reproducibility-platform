import io
import json
import zipfile

import pytest

from workbench.exports import verify_bundle
from workbench.extraction import lexical, validate_proposals


def test_bundle_rejects_traversal_and_unlisted_files():
    for name in ["../escape", "extra"]:
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as z:
            z.writestr("manifest.json", json.dumps({"files": {}}))
            z.writestr(name, "bad")
        with pytest.raises(ValueError):
            verify_bundle(data.getvalue())


def test_extraction_requires_real_quote_and_evidence():
    source = {"segments": [{"id": "s:1", "text": "The data are GSE63310 and use TMM."}]}
    result = validate_proposals(lexical(source), source)
    assert next(x for x in result if x["key"] == "accession")["value"] == "GSE63310"
    field = {
        "key": "min_count",
        "value": 10,
        "origin": "reported",
        "evidence_ids": ["s:1"],
        "quote": "10",
        "explanation": "Guess",
    }
    with pytest.raises(ValueError):
        validate_proposals([field], source)
    field.update(key="accession", value="GSE63310", quote="GSE63310", evidence_ids=["invented"])
    with pytest.raises(ValueError):
        validate_proposals([field], source)
    field.update(key="shell_command", evidence_ids=["s:1"])
    with pytest.raises(ValueError):
        validate_proposals([field], source)


def test_budget_rejects_provider_call_before_spending(service, monkeypatch):
    from workbench.extraction import assist
    from workbench.service import Problem

    service.settings.model_url = "https://model.example/chat/completions"
    service.settings.model_key = "test-only-key"
    service.settings.model_name = "test-model"
    service.settings.model_input_per_million = 1
    service.settings.model_output_per_million = 2
    service.settings.model_budget_usd = 0
    workspace = service.workspace("alice", "Budget test")

    def unexpected(*args, **kwargs):
        raise AssertionError("Provider must not be called")

    monkeypatch.setattr("workbench.extraction.httpx.post", unexpected)
    with pytest.raises(Problem) as error:
        assist(service, workspace, "alice", "law2018")
    assert error.value.status == 429


def test_invalid_model_proposal_retains_spend_reservation(service, monkeypatch):
    from types import SimpleNamespace

    from sqlalchemy import select

    from workbench.database import model_calls
    from workbench.extraction import assist
    from workbench.service import Problem

    service.settings.model_url = "https://model.example/chat/completions"
    service.settings.model_key = "test-only-key"
    service.settings.model_name = "test-model"
    service.settings.model_input_per_million = 1
    service.settings.model_output_per_million = 2
    workspace = service.workspace("alice", "Budget test")
    response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "fields": [
                                {
                                    "key": "min_count",
                                    "value": 10,
                                    "origin": "reported",
                                    "evidence_ids": ["invented"],
                                    "explanation": "Unsupported",
                                    "quote": "10",
                                }
                            ]
                        }
                    )
                }
            }
        ]
    }
    monkeypatch.setattr(
        "workbench.extraction.httpx.post",
        lambda *args, **kwargs: SimpleNamespace(raise_for_status=lambda: None, json=lambda: response),
    )
    with pytest.raises(Problem) as error:
        assist(service, workspace, "alice", "law2018")
    assert error.value.status == 502
    with service.db.transaction() as c:
        row = c.execute(select(model_calls)).mappings().one()
    assert row["reserved"] > 0 and row["actual"] is None and row["body"]["status"] == "failed"
