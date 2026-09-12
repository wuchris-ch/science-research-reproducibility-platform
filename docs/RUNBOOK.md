# Operating the workbench

This guide describes the implemented local profile. The [team deployment guide](../deploy/README.md) describes a separate configuration. All commands run from the repository root unless stated otherwise.

## Setup and configuration

Use `make setup`, then `make serve` and `make worker` in separate terminals. The UI/API use port 8317; optional Vite development uses port 3000. `uv run workbench doctor` prints the data directory, fixture availability and execution image. Configure overrides through environment variables or an untracked `.env` copied from `.env.example`.

`WORKBENCH_DATA_DIR` must be an absolute private directory shared by API and worker. `WORKBENCH_DATABASE_URL` defaults to a SQLite database in that directory. The default Docker context is `colima-research`; no command changes the user's default context. On another engine, supply the context explicitly.

`uv run workbench setup` reconstructs datasets from pinned archives, fetches and renders the verified publisher pages, builds the scientific image, records `runtime.json`, and initializes schema version 1. `uv run workbench build` performs the same source-integrity reconstruction before rebuilding and registering the runtime. It does not mutate completed runs. Existing image IDs must remain available while queued/running jobs still reference them.

A hash mismatch is a failed integrity gate. Preserve the old bytes and investigate source/version changes before deliberately changing a fixture ledger. Do not update hashes merely to make a download succeed. Network and publisher availability can affect first setup; a valid cached archive is reused without a request.

## Daily workflow and inspection

A new local installation has no research workspace. Create one in the UI, choose a supported paper/result, inspect source evidence, revise parameters with a reason if needed, check each required review field, and lock. Locked revisions cannot be edited. Variations create new plans with their parent and rationale preserved.

A submitted run has an immutable plan/runtime identity and an idempotency key. It progresses through queued, running and a terminal state. Scientific comparison and human review remain separate. Refreshing the page preserves the selected workspace, analysis, run and tab. Activity shows persisted events; Results exposes artifacts, source provenance, diagnostics and review notes. The authenticated `/api/workspaces/{id}/stream` endpoint supports `Last-Event-ID` replay; the UI currently uses bounded polling.

`GET /api/health` reports database reachability and returns 503 when the query fails. It does not certify worker availability or source completeness. Use `workbench doctor` plus a fresh small run to test the execution path. A queue that does not advance usually means the worker is stopped, the Docker engine is unavailable, or an active job belongs to another engine.

## Restart and recovery

Stop the API or worker with Control-C. Restart them using the same data directory, database, and Docker context. A worker lease expires after 30 seconds by default. A successor worker on the same engine reconciles durable container intent and sealed receipts before continuing. An old owner cannot commit a terminal result after losing its fence.

Cancel from the UI. A running cancellation remains pending until the supervisor has stopped the container and verified termination. If the Docker engine is unreachable, restore connectivity and restart the worker; do not manually relabel the run as cancelled. A missing container before receipt collection may be retried up to three attempts. OOM and timeout failures are terminal and do not automatically consume more attempts. A missing registered image is an actionable failure: rebuild/load that exact image or submit a fresh reviewed run against the new registration.

The scientific process has a wall limit of 600 seconds by default, configurable from 5 to 1,800 seconds. A supervisor enforces an additional 60-second reconciliation allowance. Each sandbox has 128 MB `/work`, 16 MB `/tmp`, a 64 MB per-file limit, 96 processes, no network, no host bind mounts and declared CPU/memory limits. Collection rejects unsafe paths and unsupported file types. Logs and outputs are bounded. The collector uses `docker exec tar` while the container is still alive because the tested daemon could not expose tmpfs output through `docker cp`.

Use `docker --context colima-research ps -a --filter label=research.workbench=true` to inspect application containers. Match the `research.run` label and epoch to the durable attempt before manual intervention. Do not remove a container whose ownership or work status is uncertain. The API needs no Docker access.

## Backup and restore

For the default SQLite profile:

```sh
uv run workbench backup /absolute/path/to/new-backup-directory
uv run workbench restore /absolute/path/to/backup-directory /absolute/path/to/new-restored-directory
```

Backups snapshot the database using SQLite's backup API, then copy append-only artifacts and staged source/data files. Protect the backup as research data. Restore requires a new directory, verifies referenced run artifacts, and marks in-flight jobs failed with an audit event because runtime ownership was not transferred. It intentionally excludes the session secret. Set `WORKBENCH_DATA_DIR` to the restored directory, run `workbench build` to register its runtime, then start API and worker. The original installation is not modified. Test the restored UI and one fresh run before relying on a backup.

For PostgreSQL, quiesce API and worker writes, take a `pg_dump --format=custom` snapshot of the intended database, copy the shared data directory, and resume services. Restore into a new database and a new data directory with matching application revision. Do not reconnect restored metadata to the original runtime while active attempts exist. The automated restore command currently supports SQLite only; PostgreSQL restoration and active-attempt reconciliation require an operator-reviewed procedure. The isolated PostgreSQL test harness does not establish production backup restoration.

## Reproducibility exports

Download a ZIP from a terminal run's Results tab. Successful runs include hashes, source/data provenance, exact collected recipe/environment files, plan/revision history, numerical artifacts, logs, receipts and a standalone Python rerun script. Failed runs are useful diagnostic exports but do not imply reproducibility success.

Extract a trusted bundle into a fresh directory and run there:

```sh
python3 reproduce.py --verify-only
python3 reproduce.py --context colima-research
```

The first command checks every manifest file; it does not authenticate the sender. The second downloads missing pinned package archives, builds the included runtime and executes it under declared limits. Review code before running a bundle from another person. Numerical comparisons and the new image identity are written under `rerun/`. A new image ID alone is not a scientific mismatch because build metadata can differ.

## Optional model assistance

Set `WORKBENCH_MODEL_URL`, `WORKBENCH_MODEL_KEY`, `WORKBENCH_MODEL_NAME` and both per-million token prices. The endpoint must be HTTPS and implement chat-completions responses with usage accounting. Keys stay server-side. The broker reserves a conservative maximum against the workspace budget before a request. Ambiguous failure retains that reservation; a retry does not silently release possible spend. Calls are scoped to a workspace and bounded source context.

The default workspace budget is USD 2. This is an internal accounting bound, not a substitute for a provider account's own hard spending control. No live provider was used in verification. Proposals show reported, inferred or missing status and linked quotes. A reviewer must resolve and lock methods explicitly.

## Verification and maintenance

Run `make check` after code changes and `make contracts` after route/schema changes. Commit the regenerated OpenAPI and TypeScript files together. CI repeats these checks plus PostgreSQL tests. Run `make science` after a recipe, dependency, count input or scientific comparator changes. Run `make runtime-checks` after supervisor/isolation changes. The scientific harness creates fresh executions on every invocation and updates its evidence receipt.

Schema migration is currently additive version 1. `uv run workbench migrate` verifies/applies it without starting a server. Future schema changes must have explicit versioned migrations, rollback/recovery documentation and compatibility checks before a release. No destructive migration or production deployment is part of local setup.
