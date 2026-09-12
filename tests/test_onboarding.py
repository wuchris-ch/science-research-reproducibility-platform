import pytest
from test_inputs import paired_tables

from workbench.documents import process_document
from workbench.evidence_graph import REQUIRED_METHODS
from workbench.onboarding import MethodDecision, Onboarding, OnboardingCreate
from workbench.schemas import LockRequest, PlanCreate
from workbench.service import REQUIRED_REVIEW, Problem

PAPER = b"""<article><body><p id="methods">Human airway muscle cells. We use raw counts. Each treated sample is paired with an untreated sample from the same donor.</p><preformat>~ cell + dex</preformat><preformat>dex trt vs untrt</preformat><preformat>rowSums(counts(dds)) &gt; 1</preformat></body></article>"""


def test_source_regions_are_inert_and_hash_addressed():
    parsed = process_document(PAPER, "xml")
    assert parsed["segments"][0]["xml_id"] == "methods"
    assert all(s["source_sha256"] == parsed["sha256"] for s in parsed["segments"])
    with pytest.raises(ValueError):
        process_document(b'<!DOCTYPE foo [<!ENTITY x SYSTEM "file:///etc/passwd">]><p>&x;</p>', "xml")


def test_onboarding_blocks_mismatch_and_unreviewed_evidence_then_seals(service):
    workflow = Onboarding(service)
    workspace = service.workspace("alice", "Lab")
    item = workflow.create("alice", OnboardingCreate(workspace_id=workspace, title="New study"))
    identity = item["id"]
    item = workflow.upload("alice", identity, item["revision"], "paper", "paper.xml", "xml", PAPER)
    with pytest.raises(Problem):
        workflow.seal("alice", identity, item["revision"])
    counts, samples = paired_tables()
    for name, data in (("counts", counts), ("samples", samples.replace(b"s5", b"s9"))):
        item = workflow.upload("alice", identity, item["revision"], name, name + ".tsv", "tsv", data)
    item = workflow.validate("alice", identity, item["revision"])
    assert "bijection" in item["body"]["issues"][0]
    item = workflow.upload("alice", identity, item["revision"], "samples", "samples.tsv", "tsv", samples)
    item = workflow.validate("alice", identity, item["revision"])
    assert item["body"]["validation"]["samples"] == 6
    with pytest.raises(Problem):
        workflow.seal("alice", identity, item["revision"])
    for key, value in REQUIRED_METHODS.items():
        field = item["body"]["fields"][key]
        item = workflow.decide(
            "alice",
            identity,
            MethodDecision(
                expected_revision=item["revision"],
                key=key,
                value=value,
                origin="inferred",
                evidence_ids=[field["candidates"][0]["evidence_id"]],
                reason="Reviewed source context and explicit mapping to the adapter",
            ),
        )
    sealed = workflow.seal("alice", identity, item["revision"])
    assert sealed["state"] == "sealed"
    assert sealed["body"]["evidence_graph"]["edges"]
    with pytest.raises(Problem):
        workflow.upload("alice", identity, sealed["revision"], "samples", "samples.tsv", "tsv", samples)
    plan = service.new_plan(
        "alice",
        PlanCreate(
            workspace_id=workspace, title="Imported", dataset_id="import_" + identity, recipe="deseq2"
        ),
    )
    locked = service.lock(
        "alice", plan["id"], LockRequest(expected_revision=1, reviewed_fields=REQUIRED_REVIEW)
    )
    assert locked["body"]["input_hash"] == sealed["body"]["input_hash"]
    assert service.store.read(locked["body"]["inputs"]["counts.tsv"]["sha256"]) == counts
    with pytest.raises(Problem):
        service.source("import_" + identity, "bob")
    other = service.workspace("alice", "Other")
    with pytest.raises(Problem):
        service.new_plan(
            "alice",
            PlanCreate(workspace_id=other, title="Bad", dataset_id="import_" + identity, recipe="deseq2"),
        )


def test_new_conflicting_source_resets_reviews(service):
    flow = Onboarding(service)
    workspace = service.workspace("alice", "Lab")
    item = flow.create("alice", OnboardingCreate(workspace_id=workspace, title="Conflicting"))
    item = flow.upload("alice", item["id"], item["revision"], "paper", "paper.xml", "xml", PAPER)
    item = flow.decide(
        "alice",
        item["id"],
        MethodDecision(
            expected_revision=item["revision"],
            key="organism",
            value="Homo sapiens",
            origin="reported",
            evidence_ids=[item["body"]["segments"][0]["id"]],
            reason="Human cells in the source",
        ),
    )
    item = flow.upload(
        "alice",
        item["id"],
        item["revision"],
        "supplement",
        "supp.xml",
        "xml",
        b"<article><p>Mouse mammary cells were used.</p></article>",
    )
    assert item["body"]["fields"]["organism"]["status"] == "conflicting"
