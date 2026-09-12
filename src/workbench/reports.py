"""Portable read-only study explorer, derived entirely from sealed artifacts."""

import base64
import csv
import gzip
import html
import io
from pathlib import Path

from .artifacts import canonical
from .database import plans
from .sensitivity import analyze


def rows(store, run, name):
    return list(
        csv.DictReader(
            io.StringIO(store.read(run["body"]["artifacts"][name]["sha256"]).decode()), delimiter="\t"
        )
    )


def report_data(service, study, base_run, analysis=None):
    result = analysis or analyze(study, service.store)
    effects = {r["gene_id"]: r for r in rows(service.store, base_run, "effects.tsv")}
    counts = {r["gene_id"]: r for r in rows(service.store, base_run, "normalized-counts.tsv")}
    samples = rows(service.store, base_run, "samples.tsv")
    plan = base_run["body"]["plan"]
    with service.db.transaction() as c:
        base_plan = service.db.row(c, plans, study["body"]["base_plan_id"])
    graph = base_plan["body"].get("evidence_graph", {})
    genes = []
    for g in result["genes"]:
        effect = effects.get(g["gene_id"], {})
        genes.append(
            [
                g["gene_id"],
                g["classification"],
                g["detections"],
                float(effect["baseMean"]) if effect.get("baseMean") not in (None, "NA") else None,
                [
                    [e[k] for k in ("log2fc", "se", "padj", "family_padj", "status", "pvalue")]
                    for e in g["estimates"]
                ],
                [float(counts[g["gene_id"]][s["sample"]]) for s in samples] if g["gene_id"] in counts else [],
            ]
        )
    return {
        "schema_version": 1,
        "title": study["body"]["title"],
        "study_id": study["id"],
        "protocol": study["body"],
        "summary": {k: v for k, v in result.items() if k != "genes"},
        "genes": genes,
        "gene_columns": [
            "gene_id",
            "classification",
            "detections",
            "reference_base_mean",
            "estimates",
            "reference_normalized_counts",
        ],
        "estimate_columns": ["log2fc", "se", "within_variant_padj", "family_padj", "status", "pvalue"],
        "samples": samples,
        "reference": {
            "run_id": base_run["id"],
            "comparison": base_run["body"].get("comparison"),
            "plan_hash": plan["plan_hash"],
            "artifacts": base_run["body"]["artifacts"],
            "adapter": plan["adapter"],
        },
        "evidence_graph": graph,
        "source_documents": base_plan["body"].get("source_documents", []),
    }


def render_report(data):
    payload = base64.b64encode(gzip.compress(canonical(data), mtime=0)).decode()
    template = (Path(__file__).parent / "report_assets/study.html").read_text()
    return template.replace("{{TITLE}}", html.escape(data["title"])).replace("{{DATA}}", payload).encode()
