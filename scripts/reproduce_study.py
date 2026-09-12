#!/usr/bin/env python3
"""Verify a deduplicated family bundle and replay selected or all completed variants."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def safe(root, name):
    path = Path(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError("Unsafe manifest path")
    target = root / path
    if target.is_symlink() or any(p.is_symlink() for p in target.parents if p != root.parent):
        raise ValueError("Symlinks are not permitted in a replay bundle")
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", default="")
    parser.add_argument("--variant", type=int, help="One variant ordinal; omit to replay all")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    manifest = json.loads((root / "manifest.json").read_text())
    for name, entry in manifest["files"].items():
        data = safe(root, name).read_bytes()
        if len(data) != entry["bytes"] or hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise ValueError("Integrity failure: " + name)
    family = json.loads((root / "family.json").read_text())
    print("Verified", len(manifest["files"]), "family files", flush=True)
    if args.verify_only:
        return
    selected = [v for v in family["variants"] if args.variant is None or v["ordinal"] == args.variant]
    if not selected:
        raise ValueError("Variant does not exist")
    for variant in selected:
        if variant["state"] != "succeeded":
            print("Variant", variant["ordinal"], "was", variant["state"], "; retained as a diagnostic record")
            continue
        target = root / "replayed" / str(variant["ordinal"])
        target.mkdir(parents=True, exist_ok=False)
        for name, entry in variant["files"].items():
            source_name = "blobs/" + entry["sha256"]
            if source_name not in manifest["files"]:
                raise ValueError("Unlisted family object")
            output = safe(target, name)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(safe(root, source_name).read_bytes())
        subprocess.run([sys.executable, str(target / "reproduce.py"), "--context", args.context], check=True)


if __name__ == "__main__":
    main()
