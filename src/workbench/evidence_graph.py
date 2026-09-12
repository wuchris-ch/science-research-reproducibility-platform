"""Source proposals and reviewer decisions are distinct graph nodes."""

import re

REQUIRED_METHODS = {
    "organism": "Homo sapiens",
    "count_scale": "raw integer counts",
    "design": "~ donor + condition",
    "contrast": "treated versus control",
    "sample_units": "one control and one treated per donor",
    "min_total_count": 2,
}


def propose(segments):
    candidates = {key: [] for key in REQUIRED_METHODS}

    def add(key, value, segment, origin="reported"):
        if not any(c["value"] == value and c["evidence_id"] == segment["id"] for c in candidates[key]):
            candidates[key].append({"value": value, "evidence_id": segment["id"], "origin": origin})

    for s in segments:
        t = s["text"]
        lower = t.lower()
        compact = re.sub(r"\s+", "", t)
        if re.search(r"\bhuman\b.{0,90}\b(cells?|donors?|airway|muscle)\b", lower):
            add("organism", "Homo sapiens", s)
        if re.search(r"\b(mouse|murine)\b.{0,60}\b(cells?|tissue|mammary)\b", lower):
            add("organism", "Mus musculus", s)
        if "raw counts" in lower or "original count data" in lower:
            add("count_scale", "raw integer counts", s, "inferred")
        if re.search(r"~(cell\+dex|donor\+condition)", compact):
            add("design", "~ donor + condition", s, "inferred")
        if "~dex" in compact and "~cell+dex" not in compact:
            add("design", "~ condition", s, "inferred")
        if "dex trt vs untrt" in lower:
            add("contrast", "treated versus control", s, "inferred")
        if ("paired" in lower and "untreated" in lower) or (
            s["kind"] == "table-row" and "condition:" in lower
        ):
            add("sample_units", "one control and one treated per donor", s, "inferred")
        if "rowSums(counts(dds))>1" in compact:
            add("min_total_count", 2, s, "inferred")
    return {
        key: {
            "key": key,
            "value": None,
            "status": "conflicting"
            if len({str(c["value"]) for c in cs}) > 1
            else "proposed"
            if cs
            else "missing",
            "candidates": cs[:24],
            "evidence_ids": [],
            "reason": "",
            "origin": "missing",
        }
        for key, cs in candidates.items()
    }


def graph(body):
    nodes = [
        {"id": "input:" + name, "type": "input", **entry} for name, entry in body.get("inputs", {}).items()
    ]
    nodes += [{"id": s["id"], "type": "evidence", **s} for s in body.get("segments", [])]
    nodes += [{"id": "method:" + key, "type": "method", **field} for key, field in body["fields"].items()]
    edges = []
    for key, field in body["fields"].items():
        for evidence in field["evidence_ids"]:
            edges.append({"from": evidence, "to": "method:" + key, "relation": "reviewed_support"})
        for candidate in field["candidates"]:
            edges.append(
                {
                    "from": candidate["evidence_id"],
                    "to": "method:" + key,
                    "relation": "candidate",
                    "value": candidate["value"],
                }
            )
    if body.get("validation"):
        nodes.append({"id": "alignment", "type": "validation", **body["validation"]})
        edges += [
            {"from": "input:" + name, "to": "alignment", "relation": "validated"}
            for name in body.get("inputs", {})
        ]
    return {"schema_version": 1, "nodes": nodes, "edges": edges}
