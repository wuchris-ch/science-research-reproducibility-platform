# Operating the workbench

This guide describes the implemented local profile. The [team deployment guide](../deploy/README.md) describes a separate configuration. All commands run from the repository root unless stated otherwise.

## Setup and configuration

Use `make setup`, then `make serve` and `make worker` in separate terminals. The UI/API use port 8317; optional Vite development uses port 3000. `uv run workbench doctor` prints the data directory, fixture availability and execution image. Configure overrides through environment variables or an untracked `.env` copied from `.env.example`.

`WORKBENCH_DATA_DIR` must be an absolute private directory shared by API and worker. `WORKBENCH_DATABASE_URL` defaults to a SQLite database in that directory. The default Docker context is `colima-research`; no command changes the user's default context. On another engine, supply the context explicitly.

`uv run workbench setup` reconstructs datasets from pinned archives, fetches and renders the verified publisher pages, builds the historical and paired DESeq2 images, records `runtime.json` and `runtime-deseq2.json`, and applies additive schema version 3. `uv run workbench build` performs the same source-integrity reconstruction before rebuilding and registering the runtime. Use `--profile historical` or `--profile deseq2` to rebuild one runtime. It does not mutate completed runs. Existing image IDs must remain available while queued/running jobs still reference them.

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

Set `WORKBENCH_MODEL_URL`, `WORKBENCH_MODEL_KEY`, `WORKBENCH_MODEL_NAME` and both per-million token prices. Set `WORKBENCH_MODEL_MODE` to `chat` or `responses` for the configured API shape. The endpoint must use HTTPS or a strict loopback address and return usage accounting. Keys stay server-side. The broker reserves a conservative maximum against the workspace budget before a request. Ambiguous failure retains that reservation; a retry does not silently release possible spend. Calls are scoped to a workspace and bounded source context.

The default workspace budget is USD 2. This is an internal accounting bound, not a substitute for a provider account's own hard spending control. Three live calls were measured in `evidence/heldout-extraction.json`; deployment credentials and endpoint identity are supplied privately. Proposals show reported, inferred or missing status and linked quotes. A reviewer must resolve and lock methods explicitly.

## Verification and maintenance

Run `make check` after code changes and `make contracts` after route/schema changes. Commit the regenerated OpenAPI and TypeScript files together. CI repeats these checks plus PostgreSQL tests. Run `make science` after a recipe, dependency, count input or scientific comparator changes. Run `make runtime-checks` after supervisor/isolation changes. The scientific harness creates fresh executions on every invocation and updates its evidence receipt.

Schema migration is additive through version 3. Version 3 adds onboarding/revision and sensitivity/variant tables while preserving completed runs and artifacts. `uv run workbench migrate` verifies/applies it without starting a server. Future schema changes must have explicit versioned migrations, rollback/recovery documentation and compatibility checks before a release. No destructive migration or production deployment is part of local setup.

## Uploaded studies and sensitivity families

Use **Onboard a study** to upload a paper, supplements, `counts.tsv` and `samples.tsv`. The count file starts with `gene_id`; every other column is a unique sample. The sample file uses `sample`, `donor`, `condition`, with one `control` and one `treated` row per donor. Validation requires exact sample alignment, at least three pairs and a full-rank design. Each table is bounded to 9 MB, 100,000 genes and 64 samples. Review every method against the linked source regions, then seal an executable plan. Corrections and validation failures remain in the revision history.

In **Sensitivity studies**, select the locked plan, state the hypothesis and register two to eight variants using the adapter's allowed choices. Registration freezes the matrix, shared input hash, adapter version, runtime, limits, family alpha and minimum effect. Start or cancel the family from the same panel. A restarted worker resumes durable scheduling; cancelled, failed and unsubmitted outcomes remain visible. Revoked scheduling access cancels the affected family.

Download the family ZIP after it reaches a terminal state. In a fresh directory:

```sh
python3 reproduce_study.py --verify-only
python3 reproduce_study.py --variant 1 --context colima-research
```

Omit `--variant` to replay all completed variants. `study.html` opens the offline explorer in a modern browser supporting gzip decompression. The archive deduplicates exact inputs and source documents and lists every registered outcome, including failures. Pointwise uncertainty intervals and within-run BH results are distinct from the family-wide BY criterion.

## Public example releases

The GitHub workflow runs tests and contract checks; a push or PR merge does not deploy a service automatically. The public service is the static explorer configured in `.openai/hosting.json`. Publish the committed `public-example/index.html` as `dist/index.html` using Sites, retaining the exact merged Git SHA in the saved version. Attach the verified family ZIP and its checksum to the matching GitHub release. Verify anonymous HTTP access, deployed content identity, functional gene exploration and the release download. The execution API remains local unless a separately configured team deployment is requested.
