"""Workspace-scoped, paginated gene exploration over sealed numerical artifacts."""

import csv
import io
from functools import lru_cache

from fastapi import Depends, Query

from .sensitivity import analyze
from .studies import Studies


@lru_cache(maxsize=4)
def table(data):
    return list(csv.DictReader(io.StringIO(data.decode()), delimiter="\t"))


def numeric(row):
    return {
        key: (value if key in ("gene_id", "status") else None if value == "NA" else float(value))
        for key, value in row.items()
    }


def register_exploration(app, service, actor):
    def get_run(who, identity):
        with service.db.transaction() as c:
            run = service.get_run(c, who, identity)
        from .service import Problem

        if run["state"] != "succeeded" or "effects.tsv" not in run["body"]["artifacts"]:
            raise Problem(409, "This execution has no complete differential result")
        return run

    def read(run, name):
        return table(service.store.read(run["body"]["artifacts"][name]["sha256"]))

    @app.get("/api/runs/{identity}/genes")
    def genes(
        identity: str,
        q: str = Query(default="", max_length=100),
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=40, ge=1, le=200),
        who=Depends(actor),
    ):
        run = get_run(who, identity)
        selected = [r for r in read(run, "effects.tsv") if q.lower() in r["gene_id"].lower()]
        selected.sort(
            key=lambda r: (
                r["pvalue"] == "NA",
                float(r["pvalue"]) if r["pvalue"] != "NA" else 1,
                r["gene_id"],
            )
        )
        return {"total": len(selected), "rows": [numeric(r) for r in selected[offset : offset + limit]]}

    @app.get("/api/runs/{identity}/genes/{gene}")
    def gene(identity: str, gene: str, who=Depends(actor)):
        from .service import Problem

        run = get_run(who, identity)
        result = next((r for r in read(run, "effects.tsv") if r["gene_id"] == gene), None)
        normalized = next((r for r in read(run, "normalized-counts.tsv") if r["gene_id"] == gene), None)
        if not result or not normalized:
            raise Problem(404, "Gene not found")
        samples = read(run, "samples.tsv")
        return {
            "gene": numeric(result),
            "samples": [{**s, "normalized_count": float(normalized[s["sample"]])} for s in samples],
            "input_hash": run["body"]["plan"].get("input_hash"),
            "plan_hash": run["body"]["plan"]["plan_hash"],
            "adapter_sha256": run["body"]["plan"]["adapter"]["sha256"],
            "image_id": run["body"]["image_id"],
            "effects_sha256": run["body"]["artifacts"]["effects.tsv"]["sha256"],
            "onboarding_id": run["body"]["plan"].get("onboarding_id"),
        }

    # Completed result families are immutable. Keep one derived analysis in memory.
    cache = {}

    def analysis(who, identity):
        with service.db.transaction() as c:
            study = Studies(service).get(c, who, identity)
        key = (identity, tuple((v["run_id"], v["state"]) for v in study["variants"]))
        if key not in cache:
            value = analyze(study, service.store)
            cache.clear()
            cache[key] = value
        return cache[key]

    @app.get("/api/studies/{identity}/results")
    def study_results(
        identity: str,
        q: str = Query(default="", max_length=100),
        classification: str = "",
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=40, ge=1, le=200),
        who=Depends(actor),
    ):
        result = analysis(who, identity)
        selected = [
            r
            for r in result["genes"]
            if q.lower() in r["gene_id"].lower()
            and (not classification or r["classification"] == classification)
        ]
        return {
            **{k: v for k, v in result.items() if k != "genes"},
            "total": len(selected),
            "genes": selected[offset : offset + limit],
        }
