"""Pinned public airway input preparation and the independently registered DESeq2 runtime."""

import json
import shutil
import subprocess

from .config import ROOT
from .fixtures import fetch, source_document
from .inputs import validate_paired
from .runner import Docker
from .runtime import register


def build_airway(settings):
    settings.initialize()
    context = settings.data_dir / "build-deseq2"
    context.mkdir(exist_ok=True)
    data = context / "data"
    data.mkdir(exist_ok=True)
    ledger = json.loads((ROOT / "fixtures/airway-data.json").read_text())
    archive = settings.data_dir / "sources/airway_0.102.0.tar.gz"
    fetch(ledger["url"], archive, ledger["sha256"], cap=20_000_000)
    for source, target in [
        ("environments/deseq2.Dockerfile", "Dockerfile"),
        ("environments/deseq2-packages.json", "locked-packages.json"),
        ("environments/entrypoint.sh", "entrypoint.sh"),
        ("recipes/deseq2.R", "run.R"),
    ]:
        shutil.copyfile(ROOT / source, context / target)
    runtime_settings = settings.model_copy(update={"image": "research-workbench-r:deseq2"})
    docker = Docker(runtime_settings)
    # Preparation is a trusted build step. No host directories are mounted into the container.
    shutil.copyfile(archive, data / "airway.tar.gz")
    subprocess.run(
        docker.prefix + ["build", "--platform", "linux/amd64", "-t", "research-deseq2:prepare", str(context)],
        check=True,
    )
    import uuid

    name = "research-airway-prepare-" + uuid.uuid4().hex[:12]
    dataset = settings.data_dir / "datasets/airway2015"
    dataset.mkdir(exist_ok=True)
    try:
        docker.command(
            [
                "run",
                "-d",
                "--name",
                name,
                "--network",
                "none",
                "--read-only",
                "--user",
                "1000:1000",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--memory",
                "2g",
                "--cpus",
                "2",
                "--tmpfs",
                "/work:rw,nosuid,nodev,noexec,size=128m,uid=1000,gid=1000",
                "--tmpfs",
                "/tmp:rw,nosuid,nodev,noexec,size=16m,uid=1000,gid=1000",
                "--entrypoint",
                "sleep",
                "research-deseq2:prepare",
                "300",
            ]
        )
        result = subprocess.run(
            docker.prefix + ["exec", "-i", name, "Rscript", "-"],
            input=(ROOT / "recipes/prepare-airway.R").read_bytes(),
            capture_output=True,
            timeout=90,
        )
        if result.returncode:
            raise RuntimeError("Historical airway conversion failed: " + result.stderr.decode()[-2000:])
        for filename in ("counts.tsv", "samples.tsv", "supplement.tsv"):
            content = docker.command(["exec", name, "cat", "/work/" + filename]).stdout.encode()
            if len(content) > 9_000_000:
                raise ValueError("Prepared input exceeds contract limit")
            (dataset / filename).write_bytes(content)
    finally:
        docker.stop(name)
        docker.remove(name)
    result = validate_paired((dataset / "counts.tsv").read_bytes(), (dataset / "samples.tsv").read_bytes())
    if result["input_genes"] != ledger["input_genes"] or result["samples"] != ledger["samples"]:
        raise ValueError("Historical airway dimensions changed")
    (settings.data_dir / "sources/airway-input-validation.json").write_text(json.dumps(result, indent=2))
    shutil.rmtree(data)
    (data / "airway2015").mkdir(parents=True)
    for filename in ("counts.tsv", "samples.tsv"):
        shutil.copyfile(dataset / filename, data / "airway2015" / filename)
    subprocess.run(
        docker.prefix + ["build", "--platform", "linux/amd64", "-t", runtime_settings.image, str(context)],
        check=True,
    )
    identity = register(runtime_settings, docker, "deseq2")
    # Preserve PDF regions and a complete JATS source for paper review.
    from .adapters import datasets

    source = datasets()["airway2015"]
    path = settings.data_dir / "sources/airway2015.xml"
    fetch(source["url"], path, source["sha256"])
    document = source_document(path, "airway2015")
    document["input_validation"] = result
    (settings.data_dir / "sources/airway2015.json").write_text(json.dumps(document))
    print("Registered DESeq2 runtime:", identity["image_id"])
    return result
