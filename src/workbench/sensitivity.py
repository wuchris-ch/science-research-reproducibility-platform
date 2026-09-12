"""Family-wide inference and gene-level stability from complete immutable outputs."""

import csv
import io
import math

from .statistics import adjust


def analyze(study, store):
    variants = study["variants"]
    tables = []
    genes = None
    for variant in variants:
        run = variant.get("run")
        rows = {}
        if run and run["state"] == "succeeded":
            entry = run["body"]["artifacts"]["effects.tsv"]
            values = list(csv.DictReader(io.StringIO(store.read(entry["sha256"]).decode()), delimiter="\t"))
            rows = {r["gene_id"]: r for r in values}
            if len(rows) != len(values):
                raise ValueError("Duplicate effect rows")
            if genes is not None and genes != set(rows):
                raise ValueError("Variants do not share the complete gene universe")
            genes = set(rows)
        tables.append(rows)
    complete = bool(variants) and all(v["state"] == "succeeded" for v in variants)
    summary = {
        "protocol_hash": study["body"]["protocol_hash"],
        "state": study["state"],
        "planned_variants": len(variants),
        "completed_variants": sum(bool(t) for t in tables),
        "complete": complete,
        "alpha": study["body"]["alpha"],
        "min_abs_log2fc": study["body"]["min_abs_log2fc"],
        "multiplicity": study["body"]["multiplicity"],
        "variants": [
            {
                "ordinal": v["ordinal"],
                "parameters": v["body"]["parameters"],
                "state": v["state"],
                "run_id": v["run_id"],
                "diagnostic": v["run"]["body"].get("diagnostic") if v.get("run") else None,
                "metrics": v["run"]["body"].get("comparison", {}).get("metrics")
                if v.get("run") and v["run"]["body"].get("comparison")
                else None,
            }
            for v in variants
        ],
    }
    if genes is None:
        return {**summary, "genes": [], "counts": {}, "family_hypotheses": 0}
    ids = sorted(genes)
    # P=1 for untested/missing cells retains the entire prespecified family size.
    cells, ps = [], []
    for ordinal, table in enumerate(tables):
        for gene in ids:
            row = table.get(gene)
            if row and row["pvalue"] != "NA":
                ps.append(float(row["pvalue"]))
                cells.append((ordinal, gene))
    family_size = len(ids) * len(variants)
    corrected = dict(zip(cells, adjust(ps, "BY", universe=family_size), strict=True))
    result, counts = [], {}
    alpha, effect_min = summary["alpha"], summary["min_abs_log2fc"]
    for gene in ids:
        estimates, directions, effects, detected, supported = [], [], [], [], []
        for ordinal, table in enumerate(tables):
            row = table.get(gene)
            lfc = float(row["log2FoldChange"]) if row and row["log2FoldChange"] != "NA" else None
            se = float(row["lfcSE"]) if row and row["lfcSE"] != "NA" else None
            q = float(row["padj"]) if row and row["padj"] != "NA" else None
            family_q = corrected.get((ordinal, gene), 1.0)
            estimates.append(
                {
                    "variant": ordinal + 1,
                    "log2fc": lfc,
                    "se": se,
                    "ci95": [lfc - 1.96 * se, lfc + 1.96 * se]
                    if lfc is not None and se is not None
                    else None,
                    "pvalue": float(row["pvalue"]) if row and row["pvalue"] != "NA" else None,
                    "padj": q,
                    "family_padj": family_q,
                    "status": row["status"] if row else "variant_unavailable",
                }
            )
            if lfc is not None:
                if not math.isfinite(lfc):
                    raise ValueError("Invalid effect size")
                effects.append(lfc)
                directions.append(1 if lfc > 0 else -1 if lfc < 0 else 0)
            detected.append(q is not None and q < alpha)
            supported.append(family_q < alpha and lfc is not None and abs(lfc) >= effect_min)
        consistent = len(effects) == len(variants) and len(set(directions)) == 1 and 0 not in directions
        robust = complete and consistent and all(supported)
        if not complete:
            label = "incomplete_family"
        elif robust:
            label = "family_supported"
        elif len(effects) < len(variants):
            label = "filter_sensitive" if effects else "not_estimated"
        elif len(set(directions)) > 1:
            label = "direction_sensitive"
        elif any(detected) and not all(detected):
            label = "threshold_sensitive"
        elif all(detected):
            label = "consistent_within_variant"
        else:
            label = "below_threshold"
        counts[label] = counts.get(label, 0) + 1
        result.append(
            {
                "gene_id": gene,
                "classification": label,
                "consistent_direction": consistent,
                "min_log2fc": min(effects) if effects else None,
                "max_log2fc": max(effects) if effects else None,
                "detections": sum(detected),
                "estimates": estimates,
            }
        )
    result.sort(key=lambda g: (g["classification"] != "family_supported", -g["detections"], g["gene_id"]))
    return {
        **summary,
        "genes": result,
        "counts": counts,
        "family_hypotheses": family_size,
        "interval_scope": "Approximate pointwise 95% intervals from reported coefficient SE; intervals are not simultaneous across the family",
    }
