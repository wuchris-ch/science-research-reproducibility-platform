"""Run the contract suite against a disposable loopback-only PostgreSQL container."""

import json
import os
import secrets
import subprocess
import time

from workbench.config import ROOT, Settings
from workbench.runner import Docker

s = Settings()
docker = Docker(s)
password = secrets.token_hex(24)
name = "research-postgres-check"
if docker.inspect(name):
    raise RuntimeError("Existing test container found; inspect it before running again")
try:
    docker.command(
        [
            "run",
            "-d",
            "--name",
            name,
            "--label",
            "research.workbench.test=true",
            "-p",
            "127.0.0.1::5432",
            "-e",
            "POSTGRES_PASSWORD=" + password,
            "--tmpfs",
            "/var/lib/postgresql/data:rw,size=256m",
            "postgres:16-alpine",
        ],
        timeout=60,
    )
    info = docker.inspect(name)
    port = info["NetworkSettings"]["Ports"]["5432/tcp"][0]["HostPort"]
    for _ in range(30):
        if docker.command(["exec", name, "pg_isready", "-U", "postgres"], check=False).returncode == 0:
            break
        time.sleep(1)
    env = {
        **os.environ,
        "WORKBENCH_TEST_POSTGRES_URL": f"postgresql+psycopg://postgres:{password}@127.0.0.1:{port}/postgres",
    }
    result = subprocess.run(["uv", "run", "pytest", "-q"], env=env, cwd=ROOT, capture_output=True, text=True)
    print(result.stdout)
    (ROOT / "evidence/postgres-verification.json").write_text(
        json.dumps(
            {
                "date": "2026-09-11",
                "image_id": info["Image"],
                "database": "PostgreSQL 16",
                "exit_code": result.returncode,
                "test_output": result.stdout,
                "isolation": "New database per test in a disposable container; loopback port only",
            },
            indent=2,
        )
        + "\n"
    )
    if result.returncode:
        raise RuntimeError("PostgreSQL verification failed")
finally:
    docker.command(["rm", "-f", name], check=False)
