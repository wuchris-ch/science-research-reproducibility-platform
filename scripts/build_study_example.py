"""Build a read-only public example from a completed, explicitly selected study."""

import argparse
import base64
import gzip
import json
from pathlib import Path

from workbench.adapters import MANIFESTS
from workbench.artifacts import canonical
from workbench.cli import make_service
from workbench.config import ROOT, Settings
from workbench.reports import render_report, report_data, rows
from workbench.studies import Studies
from workbench.study_exports import study_bundle


def build(study_id, reference_id, output, bundle_path):
    service = make_service(Settings())
    with service.db.transaction() as c:
        study = Studies(service).get(c, "local", study_id)
        reference = service.get_run(c, "local", reference_id)
    if study["state"] != "complete" or reference["state"] != "succeeded":
        raise ValueError("Public example requires complete execution evidence")
    source = reference["body"]["plan"]["dataset_id"]
    receipt = json.loads((ROOT / "evidence/airway-study-verification.json").read_text())
    if (
        source != "airway2015"
        or reference["body"]["plan"]["input_hash"] != study["body"]["input_hash"]
        or receipt["study_id"] != study_id
        or receipt["reference_run_id"] != reference_id
        or receipt["protocol"]["protocol_hash"] != study["body"]["protocol_hash"]
        or not receipt["reference_replay"]["same_numeric_bytes"]
        or not receipt["family_variant_replay"]["same_numeric_bytes"]
    ):
        raise ValueError("The public narrative must match its verified study and replay evidence")
    data = report_data(service, study, reference)
    example = json.loads((MANIFESTS / "references.json").read_text())[source]["gene_examples"]
    effects = {r["gene_id"]: r for r in rows(service.store, reference, "effects.tsv")}
    comparison = [
        dict(g, computed_log2fc=float(effects[g["gene_id"]]["log2FoldChange"])) for g in example["values"]
    ]
    data["public_notes"] = {
        "registration": "The initial reference result was available before this family was registered.",
        "discrepancy": "The pinned runtime retained 29,391 genes, matching the source. It found 4,822 significant genes at FDR 0.10 versus 4,897 reported. The runtime uses DESeq2 1.38.3; the source used 1.8.1.",
        "alignment": "An uploaded sample table contained SRR1039599 where the count matrix required SRR1039521. Validation rejected the mismatch at revision 7. The corrected table passed before plan locking; both revisions remain in the onboarding history.",
        "replay": "An independently extracted reference bundle rebuilt its runtime and reproduced all six numerical artifacts byte for byte: metrics, design, genes, samples, effects and normalized counts. The new image identity differs because image builds include metadata.",
        "figure": "data:image/png;base64,"
        + base64.b64encode(
            (service.settings.data_dir / ("sources/" + source + "-figure.png")).read_bytes()
        ).decode(),
        "published_genes": comparison,
        "bundle_url": "https://github.com/wuchris-ch/science-research-reproducibility-platform/releases/download/v0.2.0/airway-sensitivity.zip",
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "index.html").write_bytes(render_report(data))
    (service.settings.data_dir / "example-data.json.gz").write_bytes(gzip.compress(canonical(data), mtime=0))
    print("Built report:", output / "index.html", flush=True)
    if bundle_path:
        bundle_path.parent.mkdir(parents=True, exist_ok=True)
        bundle_path.write_bytes(study_bundle(service, study, "local"))
        print("Built family bundle:", bundle_path, bundle_path.stat().st_size, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", required=True)
    parser.add_argument("--reference-run", required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "public-example")
    parser.add_argument("--bundle", type=Path)
    args = parser.parse_args()
    build(args.study, args.reference_run, args.output, args.bundle)
