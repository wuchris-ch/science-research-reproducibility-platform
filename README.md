# Research Workbench

An evidence-linked workbench for reviewing and rerunning published bulk RNA-seq analyses. Select a paper, inspect its methods, lock a reviewed plan, execute a bounded R recipe, compare numerical results, create a controlled variation, and export the complete provenance bundle.

Implemented and locally verified on September 11, 2026. The application executes real analyses from two published datasets. Scientific agreement, execution success, and a researcher's interpretation are recorded separately.

## Start on macOS

Requires Python 3.12+, uv, Node.js 22+, npm, Docker CLI and a running Linux Docker engine. On Apple Silicon, the historical R image runs as `linux/amd64`. The verified local environment uses a dedicated Colima profile with no host mounts:

```sh
colima start research --cpus 4 --memory 8 --disk 30 --mount none --activate=false --vz-rosetta --ssh-agent=false --ssh-config=false
make setup
```

`make setup` installs locked dependencies, builds the interface, downloads and verifies public source/data archives, reconstructs the two datasets, builds the R image, registers its immutable identity, and initializes local storage. Downloads include a historical annotation archive of about 63 MB. Source downloads and builds need network access; scientific executions do not.

Start these in two terminals from this checkout:

```sh
make serve
```

```sh
make worker
```

Open [Research Workbench](http://127.0.0.1:8317). Create a workspace and analysis, review the five required method fields, lock the revision, and run. Use **Results** to inspect checks and artifacts, **Create variation** to preserve a parent analysis, and **Export reproducibility bundle** to save a portable record. To populate the same four example analyses used in verification, run `make science`; this is a verification harness, not a human scientific review.

The default profile is loopback-only, uses SQLite, and needs no account or model key. Data and logs live in `.runtime/`, which is excluded from Git. Optional settings are listed in [.env.example](.env.example). For another Docker engine, set `WORKBENCH_DOCKER_CONTEXT` to its context name. Keep the API and worker on the same data directory and database.

## What runs

| Workflow | Observed result | Interpretation |
|---|---|---|
| Law et al. v3, Figure 1 | 27,179 input genes, 9 samples, 5,153 all-zero genes, 16,624 retained | Published scalar checks match; the paper provides no density grid for exact curve comparison |
| Controlled Law filter variation | 14,165 retained genes | Matches the independent input probe; this is a sensitivity analysis |
| Law differential expression | Full 16,624-gene tested universe, 9,511 significant at BH FDR 0.05 for Basal versus LP | TMM, voom, `~0+group+lane`, eBayes; distinct from the paper's later TREAT analysis |
| Chen et al. v2, Figure 1 | 26,357 annotated genes, 15,653 retained, 12 samples | Original annotation and filtering counts match in an explicitly adapted R environment |

Fresh reference runs produced identical numerical artifact bytes. A separately extracted export rebuilt its runtime and reproduced the exported numerical files. See [implementation status and evidence](docs/IMPLEMENTED.md) and [scientific adaptations](recipes/ADAPTATIONS.md) for the exact scope.

## Development and verification

```sh
make check             # Python lint/format, contract tests, TypeScript and Vite build
make contracts         # Regenerate OpenAPI and browser types in an isolated database
make science           # Real R executions and fresh numerical comparison
make runtime-checks    # Real confinement, cancellation, timeout and OOM drills
make postgres-check    # Same contracts against disposable PostgreSQL databases
```

For frontend development, keep the API running and use `make dev-web` at [localhost:3000](http://127.0.0.1:3000). Vite proxies API calls to port 8317. The GitHub workflow runs checks, rejects contract drift, and exercises PostgreSQL. Real scientific checks are explicit local commands because they require the sealed data and runtime.

[Operating guide](docs/RUNBOOK.md) covers setup, inspection, restart, backup, restore, exports, team identity, quotas and troubleshooting. [Team deployment template](deploy/README.md) includes an API image and PostgreSQL configuration. Its image has been built and smoke-tested locally; a production deployment and live identity-provider integration have not been performed.

## Scope and design records

The optional model broker proposes source-linked fields under a spending reservation. Proposals never lock methods or execute code. Imported PDFs are stored for manual review. Execution currently supports the three curated recipes above; arbitrary uploaded code and repositories require a separate, stronger execution boundary.

The [original backlog](docs/IMPLEMENTATION.md), [architecture](docs/ARCHITECTURE.md), [verification plan](docs/VERIFICATION.md), [product research](docs/PRODUCT.md), and [source register](docs/SOURCES.md) remain as design records. [IMPLEMENTED.md](docs/IMPLEMENTED.md) maps them to delivered behavior, measured results, and deferred gates. Git history preserves meaningful implementation, correction, test and operational checkpoints.
