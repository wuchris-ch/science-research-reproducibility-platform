"""Comparators consume sealed outputs; execution never receives expected answers."""

import csv
import io
import json
import math

from .adapters import MANIFESTS
from .statistics import adjust


def validate_effects(table, metrics, plan, ids, retained, samples):
    rows = table("effects.tsv")
    if len(rows) != len(ids) or {r["gene_id"] for r in rows} != set(ids):
        raise ValueError("Effects must preserve the complete input gene universe")
    tested = []
    for row in rows:
        status = row["status"]
        if status == "excluded_low_total":
            if row["gene_id"] in retained or any(
                row[k] != "NA" for k in ("pvalue", "padj", "log2FoldChange")
            ):
                raise ValueError("Excluded gene has inconsistent statistics")
            continue
        if row["gene_id"] not in retained or status not in (
            "tested",
            "cook_outlier",
            "independently_filtered",
        ):
            raise ValueError("Invalid gene exclusion status")
        for key in ("baseMean", "log2FoldChange", "lfcSE", "stat"):
            if not math.isfinite(float(row[key])):
                raise ValueError("Non-finite retained gene statistic")
        if float(row["baseMean"]) < 0 or float(row["lfcSE"]) < 0:
            raise ValueError("Negative mean or uncertainty")
        if status == "cook_outlier":
            if row["pvalue"] != "NA" or row["padj"] != "NA":
                raise ValueError("Outlier must remain untested")
        else:
            if not 0 <= float(row["pvalue"]) <= 1:
                raise ValueError("Invalid P value")
            if status == "independently_filtered" and row["padj"] != "NA":
                raise ValueError("Independent-filter exclusion must have no adjusted P value")
            if status == "tested":
                if not 0 <= float(row["padj"]) <= 1:
                    raise ValueError("Invalid adjusted P value")
                tested.append(row)
    corrected = adjust([float(row["pvalue"]) for row in tested])
    if any(abs(value - float(row["padj"])) > 1e-10 for value, row in zip(corrected, tested, strict=True)):
        raise ValueError("DESeq2 adjusted P values differ from the declared BH universe")
    if (
        len(tested) != metrics["tested_genes"]
        or sum(float(r["padj"]) < plan["parameters"]["fdr"] for r in tested) != metrics["significant_genes"]
    ):
        raise ValueError("Differential counts do not match metrics")
    normalized = table("normalized-counts.tsv")
    if len(normalized) != len(ids) or {r["gene_id"] for r in normalized} != set(ids):
        raise ValueError("Normalized counts must preserve all genes")
    sample_ids = {s["sample"] for s in samples}
    if set(normalized[0]) != sample_ids | {"gene_id"}:
        raise ValueError("Normalized sample columns differ from the input")
    if any(not math.isfinite(float(r[s])) or float(r[s]) < 0 for r in normalized for s in sample_ids):
        raise ValueError("Invalid normalized count")


def validate_metrics(data: bytes, plan: dict):
    m = json.loads(data, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Non-finite number")))
    for field in ("input_genes", "samples", "all_zero_genes", "retained_genes"):
        if type(m.get(field)) is not int or m[field] < 0:
            raise ValueError(f"Invalid metric {field}")
    if (
        m.get("schema_version") != 1
        or m.get("recipe") != plan["recipe"]
        or m.get("dataset_id") != plan["dataset_id"]
    ):
        raise ValueError("Output contract does not match locked plan")
    if m.get("parameters") != plan["parameters"]:
        raise ValueError("Output parameters differ from locked plan")
    if m["retained_genes"] > m["input_genes"] or not 2 <= m["samples"] <= 64:
        raise ValueError("Invalid gene or sample counts")
    return m


def compare(metrics, plan):
    reference = json.loads((MANIFESTS / "references.json").read_text()).get(
        plan.get("reference_dataset", plan["dataset_id"]), {}
    )
    checks = []
    for entry in reference.get("checks", []):
        if any(plan["parameters"].get(k) != v for k, v in entry.get("when", {}).items()):
            continue
        actual = metrics.get(entry["key"])
        checks.append({**entry, "actual": actual, "passed": actual == entry["expected"]})
    for key in ("input_genes", "samples", "all_zero_genes", "library_sizes"):
        if key in plan.get("input_summary", {}):
            expected = plan["input_summary"][key]
            checks.append(
                {
                    "key": key,
                    "expected": expected,
                    "actual": metrics.get(key),
                    "passed": metrics.get(key) == expected,
                    "kind": "input_integrity",
                    "basis": "Validated immutable uploaded inputs",
                }
            )
    return {
        "status": "checks_match"
        if checks and all(c["passed"] for c in checks)
        else "mismatch"
        if checks
        else "no_reference",
        "checks": checks,
        "limitations": reference.get(
            "limitations", ["No independently reported result table is registered for this imported dataset."]
        ),
        "claim": "Checked observables only",
        "metrics": metrics,
    }


def compare_fresh(store, left, right):
    """Numeric rerun comparison separate from comparison to the publication."""
    shared = set(left) & set(right)
    results = []
    for name in sorted(shared):
        a, b = store.read(left[name]["sha256"]), store.read(right[name]["sha256"])
        if name in (
            "density.tsv",
            "effects.tsv",
            "normalized-counts.tsv",
            "differential.tsv",
            "mds.tsv",
            "genes.tsv",
            "samples.tsv",
            "design.tsv",
            "metrics.json",
        ):
            results.append({"artifact": name, "byte_equal": a == b})
    return {
        "checks": results,
        "same_numeric_bytes": bool(results)
        and all(x["byte_equal"] for x in results)
        and set(left) == set(right),
        "scope": "Fresh run artifact consistency; not independent scientific validation",
    }


def validate_tables(store, artifacts, metrics, plan):
    def table(name):
        return list(
            csv.DictReader(io.StringIO(store.read(artifacts[name]["sha256"]).decode()), delimiter="\t")
        )

    required = plan.get("adapter", {}).get("required_outputs", [])
    if set(required) - artifacts.keys():
        raise ValueError("Missing required adapter outputs")
    genes = table("genes.tsv")
    ids = [g["gene_id"] for g in genes]
    retained = {g["gene_id"] for g in genes if g["retained"] == "TRUE"}
    if (
        len(ids) != metrics["input_genes"]
        or len(set(ids)) != len(ids)
        or len(retained) != metrics["retained_genes"]
    ):
        raise ValueError("Gene universe does not match metrics")
    if any(g["retained"] not in ("TRUE", "FALSE") for g in genes):
        raise ValueError("Invalid retained gene flag")
    samples = table("samples.tsv")
    if len(samples) != metrics["samples"] or len({s["sample"] for s in samples}) != len(samples):
        raise ValueError("Invalid sample mapping")
    if {s["sample"]: int(s["library_size"]) for s in samples} != metrics["library_sizes"]:
        raise ValueError("Sample totals differ from metrics")
    if plan["recipe"] == "density":
        rows = table("density.tsv")
        if len(rows) != 2 * metrics["samples"] * 512:
            raise ValueError("Incomplete density grids")
        groups = {}
        for row in rows:
            x, y = float(row["x"]), float(row["y"])
            if not math.isfinite(x) or not math.isfinite(y) or y < -1e-12:
                raise ValueError("Invalid density value")
            groups.setdefault((row["stage"], row["sample"]), []).append((x, y))
        expected = {(stage, s["sample"]) for stage in ("raw", "filtered") for s in samples}
        if set(groups) != expected:
            raise ValueError("Unknown density series")
        for points in groups.values():
            if len(points) != 512 or any(b[0] <= a[0] for a, b in zip(points, points[1:], strict=False)):
                raise ValueError("Invalid density grid order")
            area = sum((b[0] - a[0]) * (b[1] + a[1]) / 2 for a, b in zip(points, points[1:], strict=False))
            if not 0.98 < area < 1.02:
                raise ValueError("Density area is inconsistent")
    elif plan["recipe"] == "differential":
        rows = table("differential.tsv")
        if len(rows) != len(retained) or {r["gene_id"] for r in rows} != retained:
            raise ValueError("Differential table must contain the full tested universe")
        ps = []
        for r in rows:
            p, a, f = float(r["P.Value"]), float(r["adj.P.Val"]), float(r["logFC"])
            if not all(math.isfinite(v) for v in (p, a, f)) or not 0 <= p <= a <= 1:
                raise ValueError("Invalid differential statistic")
            ps.append(p)
        n = len(rows)
        order = sorted(range(n), key=lambda i: ps[i])
        last = 1.0
        for rank in range(n, 0, -1):
            i = order[rank - 1]
            last = min(last, ps[i] * n / rank)
            if abs(last - float(rows[i]["adj.P.Val"])) > 1e-10:
                raise ValueError("Adjusted P values do not match full-universe BH correction")
    elif plan["recipe"] == "deseq2":
        validate_effects(table, metrics, plan, ids, retained, samples)
    else:
        rows = table("mds.tsv")
        if {r["sample"] for r in rows} != {s["sample"] for s in samples} or len(rows) != len(samples):
            raise ValueError("Invalid MDS sample mapping")
        if any(not math.isfinite(float(r[k])) for r in rows for k in ("x", "y")):
            raise ValueError("Invalid MDS coordinate")
