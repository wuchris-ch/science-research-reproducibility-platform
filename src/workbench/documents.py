"""Ingestion uses a bounded child with a minimal environment, separate from API state."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def process_document(data, kind, page=None):
    if len(data) > 9_000_000:
        raise ValueError("Document exceeds 9 MB")
    with tempfile.TemporaryDirectory(prefix="research-source-") as folder:
        path = Path(folder) / "source"
        path.write_bytes(data)
        args = [sys.executable, "-m", "workbench.document_worker", kind, str(path)]
        if page is not None:
            if not 1 <= page <= 100:
                raise ValueError("Page must be between 1 and 100")
            args.append(str(page))
        try:
            result = subprocess.run(
                args,
                cwd=folder,
                env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
                capture_output=True,
                timeout=25,
            )
        except subprocess.TimeoutExpired:
            raise ValueError("Document parsing exceeded its time limit") from None
        if result.returncode or len(result.stdout) > 12_000_000:
            raise ValueError("Document could not be decoded within its resource limits")
        return result.stdout if kind == "render" else json.loads(result.stdout)
