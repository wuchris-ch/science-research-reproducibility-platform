"""Comparators consume sealed outputs; execution never receives expected answers."""

import csv
import io
import json
import math

from .fixtures import EVIDENCE


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
    if m["retained_genes"] > m["input_genes"] or m["samples"] not in (9, 12):
        raise ValueError("Invalid gene or sample counts")
    return m


def compare(metrics, plan):
    checks = []

    def check(key, expected, basis):
        actual = metrics.get(key)
        checks.append(
            {"key": key, "expected": expected, "actual": actual, "passed": actual == expected, "basis": basis}
        )

    check("input_genes", 27179, "Public count matrix and paper")
    if plan["dataset_id"] == "law2018":
        check("samples", 9, "Paper sample mapping")
        check("all_zero_genes", 5153, "Paper and independent input probe")
        p = plan["parameters"]
        if p["filter_policy"] == "published" and (p["min_count"], p["min_total_count"], p["min_samples"]) == (
            10,
            15,
            3,
        ):
            check("retained_genes", 16624, "Paper v3 reported filtered universe")
        elif p["filter_policy"] == "cpm1" and p["min_samples"] == 3:
            check("retained_genes", 14165, "Independent Python filter probe; not a published result")
        expected = {
            e["member"].split("_", 1)[1].removesuffix(".txt.gz"): e["library_size"] for e in EVIDENCE["files"]
        }
        check("library_sizes", expected, "Pinned GEO sample totals")
        limitations = [
            "Paper supplies no density grid, so numerical curve agreement with the published plot is unverified.",
            "Scalar agreement is not evidence that every scientific conclusion reproduces.",
        ]
        if plan["recipe"] == "differential":
            limitations.append(
                "Full gene-level reference table is unavailable; FDR and effect sizes are exported for review."
            )
    else:
        check("samples", 12, "Paper sample mapping")
        check("annotated_genes", 26357, "Paper with org.Mm.eg.db 3.3.0")
        if plan["parameters"]["filter_policy"] == "published":
            check("retained_genes", 15653, "Paper CPM > 0.5 in two samples")
        limitations = [
            "Adapted R and edgeR versions; no published numerical MDS coordinates are available.",
            "MDS axis signs are arbitrary. Compare pairwise distances for fresh-run consistency.",
        ]
    return {
        "status": "checks_match" if all(c["passed"] for c in checks) else "mismatch",
        "checks": checks,
        "limitations": limitations,
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
    else:
        rows = table("mds.tsv")
        if {r["sample"] for r in rows} != {s["sample"] for s in samples} or len(rows) != len(samples):
            raise ValueError("Invalid MDS sample mapping")
        if any(not math.isfinite(float(r[k])) for r in rows for k in ("x", "y")):
            raise ValueError("Invalid MDS coordinate")
