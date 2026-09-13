import importlib.util

from workbench.config import ROOT

spec = importlib.util.spec_from_file_location("benchmark", ROOT / "scripts/benchmark_extraction.py")
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


def test_exact_quote_of_wrong_experiment_is_not_semantic_support():
    question = {"accepted": ["GSE64098"], "evidence_paragraphs": [14]}
    source = {"p11": "Pilot GSE86337", "p14": "Mixture GSE64098"}
    wrong = benchmark.score(
        question, {"value": "GSE86337", "quote": "GSE86337", "evidence_ids": ["p11"]}, source
    )
    assert wrong["quotation_valid"] and not wrong["passed"] and not wrong["context_correct"]
    fabricated = benchmark.score(
        question, {"value": "GSE64098", "quote": "GSE64098", "evidence_ids": ["p11"]}, source
    )
    assert fabricated["value_correct"] and not fabricated["quotation_valid"] and not fabricated["passed"]
    correct = benchmark.score(
        question, {"value": "GSE64098", "quote": "GSE64098", "evidence_ids": ["p14"]}, source
    )
    assert correct["passed"]


def test_missing_method_requires_abstention():
    question = {"accepted": [None], "evidence_paragraphs": []}
    source = {"p1": "Another tool uses TMM"}
    assert benchmark.score(question, {"value": None}, source)["passed"]
    assert not benchmark.score(question, {"value": "TMM", "quote": "TMM", "evidence_ids": ["p1"]}, source)[
        "passed"
    ]
