#!/usr/bin/env python3
"""Standalone bundle verifier and cold rerun. Uses only Python's standard library."""

import argparse
import hashlib
import json
import os
import subprocess
import time
import urllib.request
import uuid
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", default=os.environ.get("DOCKER_CONTEXT", ""))
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "manifest.json").read_text())
    for name, entry in manifest["files"].items():
        p = Path(name)
        if p.is_absolute() or ".." in p.parts:
            raise ValueError("Unsafe manifest path")
        data = (root / p).read_bytes()
        if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError("Integrity failure: " + name)
    print("Verified", len(manifest["files"]), "bundle files", flush=True)
    if args.verify_only:
        return
    replay_status = root / "replay-status.json"
    if replay_status.exists() and not json.loads(replay_status.read_text())["reproducible"]:
        raise ValueError("This diagnostic bundle does not contain complete sealed execution inputs")
    docker = ["docker"] + (["--context", args.context] if args.context else [])
    packages = root / "build/packages"
    packages.mkdir(exist_ok=True)
    for entry in json.loads((root / "locked-packages.json").read_text()):
        path = packages / entry["file"]
        if not path.exists():
            with urllib.request.urlopen(entry["url"], timeout=90) as r:
                data = r.read(20_000_001)
            if len(data) > 20_000_000:
                raise ValueError("Package too large")
            path.write_bytes(data)
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError("Package integrity failure")
    tag = "research-replay:" + manifest["run_id"][:12]
    subprocess.run(
        docker + ["build", "--platform", "linux/amd64", "-t", tag, str(root / "build")], check=True
    )
    image = subprocess.check_output(
        docker + ["image", "inspect", tag, "--format", "{{.Id}}"], text=True
    ).strip()
    plan = json.loads((root / "plan.json").read_text())
    name = "research-replay-" + uuid.uuid4().hex
    out = root / "rerun"
    out.mkdir(exist_ok=True)
    if any(out.iterdir()):
        raise ValueError("Rerun output directory must be empty; use a fresh extracted bundle")
    limits = json.loads((root / "run.json").read_text())["body"]["limits"]
    command = docker + [
        "create",
        "--name",
        name,
        "--platform",
        "linux/amd64",
        "--network",
        "none",
        "--read-only",
        "--user",
        "1000:1000",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "96",
        "--memory",
        str(limits["memory_mib"]) + "m",
        "--memory-swap",
        str(limits["memory_mib"]) + "m",
        "--cpus",
        str(limits["cpu"]),
        "--tmpfs",
        "/work:rw,nosuid,nodev,noexec,size=128m,uid=1000,gid=1000,mode=0700",
        "--tmpfs",
        "/tmp:rw,nosuid,nodev,noexec,size=16m,uid=1000,gid=1000,mode=0700",
        "-e",
        "PLAN_JSON=" + json.dumps(plan),
        "-e",
        "WALL_SECONDS=" + str(limits["wall_seconds"]),
        image,
    ]
    subprocess.run(command, check=True)
    try:
        subprocess.run(docker + ["start", name], check=True)
        deadline = time.monotonic() + limits["wall_seconds"] + 30
        while time.monotonic() < deadline:
            if (
                subprocess.run(
                    docker + ["exec", name, "test", "-f", "/work/done"], capture_output=True
                ).returncode
                == 0
            ):
                break
            time.sleep(1)
        else:
            raise TimeoutError("Rerun exceeded wall-clock limit")
        import io
        import tarfile

        content = subprocess.check_output(
            docker + ["exec", name, "tar", "-C", "/work/output", "-cf", "-", "."], timeout=30
        )
        if len(content) > 100_000_000:
            raise ValueError("Outputs exceed limit")
        with tarfile.open(fileobj=io.BytesIO(content)) as tf:
            for member in tf:
                p = Path(member.name)
                if member.isdir():
                    continue
                if not member.isfile() or p.is_absolute() or ".." in p.parts or len(p.parts) > 2:
                    raise ValueError("Unsafe output")
                (out / p).parent.mkdir(parents=True, exist_ok=True)
                (out / p).write_bytes(tf.extractfile(member).read())
        code = int((out / "exit-code").read_text())
        if code:
            raise RuntimeError("R exited " + str(code) + ": " + (out / "stderr.log").read_text())
        checks = {}
        for original in (root / "outputs").iterdir():
            if original.suffix in (".tsv", ".json"):
                p = out / original.name
                checks[original.name] = p.is_file() and p.read_bytes() == original.read_bytes()
        receipt = {
            "image_id": image,
            "original_image_id": json.loads((root / "run.json").read_text())["body"]["image_id"],
            "checks": checks,
            "same_numeric_bytes": bool(checks) and all(checks.values()),
            "scope": "Fresh bundle rerun; image rebuild may have different build metadata",
        }
        (out / "rerun-receipt.json").write_text(json.dumps(receipt, indent=2))
        print(json.dumps(receipt, indent=2))
        if not receipt["same_numeric_bytes"]:
            raise RuntimeError("Fresh numerical files differ or are missing; inspect rerun-receipt.json")
    finally:
        subprocess.run(docker + ["rm", "-f", name], capture_output=True)


if __name__ == "__main__":
    main()
