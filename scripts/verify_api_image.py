"""Smoke-test the API image without credentials, a Docker socket, or host mounts."""

import json
import time
import uuid
from datetime import UTC, datetime

from workbench.config import ROOT, Settings
from workbench.runner import Docker

docker = Docker(Settings())
name = "research-api-check-" + uuid.uuid4().hex[:12]
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
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--memory",
            "512m",
            "--pids-limit",
            "96",
            "--tmpfs",
            "/data:rw,nosuid,nodev,size=32m,uid=1000,gid=1000",
            "--tmpfs",
            "/tmp:rw,nosuid,nodev,size=16m,uid=1000,gid=1000",
            "research-workbench-api:local",
            "serve",
            "--host",
            "127.0.0.1",
            "--port",
            "8317",
        ]
    )
    result = None
    for _ in range(30):
        response = docker.command(
            [
                "exec",
                name,
                "python",
                "-c",
                "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8317/api/health', timeout=2).read().decode())",
            ],
            check=False,
        )
        if response.returncode == 0:
            result = json.loads(response.stdout)
            break
        time.sleep(1)
    assert result and result["status"] == "ok", docker.command(["logs", name]).stderr
    static = docker.command(
        [
            "exec",
            name,
            "python",
            "-c",
            "import urllib.request; assert b'Research Workbench' in urllib.request.urlopen('http://127.0.0.1:8317/').read()",
        ]
    )
    no_docker = docker.command(
        [
            "exec",
            name,
            "python",
            "-c",
            "import os, shutil; assert shutil.which('docker') is None; assert not os.path.exists('/var/run/docker.sock')",
        ]
    )
    portable_exports = docker.command(
        [
            "exec",
            name,
            "python",
            "-c",
            "from workbench.config import ROOT; assert (ROOT / 'scripts/reproduce_study.py').is_file(); from workbench.adapters import registry; assert len(registry()) == 4; from pathlib import Path; import workbench.reports as reports; assert (Path(reports.__file__).parent / 'report_assets/study.html').is_file()",
        ]
    )
    info = docker.inspect(name)
    checks = {
        "health_and_database": True,
        "static_ui": static.returncode == 0,
        "registered_adapters_and_portable_family_files": portable_exports.returncode == 0,
        "no_docker_cli_or_socket": no_docker.returncode == 0,
        "non_root": info["Config"]["User"] == "1000:1000",
        "read_only_root": info["HostConfig"]["ReadonlyRootfs"],
        "no_host_mounts": not any(m["Type"] == "bind" for m in info["Mounts"]),
    }
    assert all(checks.values())
    receipt = {
        "verified_at": datetime.now(UTC).isoformat(),
        "image_id": info["Image"],
        "checks": checks,
        "scope": "Local container image smoke test using ephemeral SQLite. Does not verify a live OIDC tenant or production deployment.",
    }
    (ROOT / "evidence/api-image-verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
finally:
    docker.command(["rm", "-f", name], check=False)
