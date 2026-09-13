from workbench.sensitivity import analyze


def test_incomplete_family_cannot_produce_supported_genes(service):
    def run(effect):
        data = f"gene_id\tlog2FoldChange\tlfcSE\tpvalue\tpadj\tstatus\ngene-a\t{effect}\t0.1\t0.000001\t0.000001\ttested\n".encode()
        return {
            "state": "succeeded",
            "body": {"artifacts": {"effects.tsv": {"sha256": service.store.put(data)}}},
        }

    study = {
        "state": "incomplete",
        "body": {"protocol_hash": "frozen", "alpha": 0.05, "min_abs_log2fc": 1, "multiplicity": "BY"},
        "variants": [
            {"ordinal": 1, "state": "succeeded", "run_id": "one", "body": {"parameters": {}}, "run": run(2)},
            {"ordinal": 2, "state": "failed", "run_id": "two", "body": {"parameters": {}}, "run": None},
        ],
    }
    result = analyze(study, service.store)
    assert result["family_hypotheses"] == 2
    assert not result["complete"] and result["counts"] == {"incomplete_family": 1}
    assert result["genes"][0]["estimates"][1]["family_padj"] == 1
    study["state"] = "complete"
    study["variants"][1].update(state="succeeded", run=run(-2))
    result = analyze(study, service.store)
    assert result["counts"] == {"direction_sensitive": 1}
    study["variants"][1]["run"] = run(2)
    assert analyze(study, service.store)["counts"] == {"family_supported": 1}
