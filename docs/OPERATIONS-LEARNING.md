# Local operation, team path and learning

[Start](../README.md) · [Backlog](IMPLEMENTATION.md) · [Architecture](ARCHITECTURE.md) · [Evaluation](VERIFICATION.md)

## Mac environment

Observed September 11, 2026: Apple Silicon (`arm64`), macOS 26.5, 64 GiB RAM. Docker CLI 29.5.2, Colima, Node, Python and uv were available; the contacted Docker server reported 20.10.16. `Rscript` was not found on PATH. No runtime was installed, upgraded or restarted. These observations do not prove the existing Docker context supports the planned isolation policy.

Keep R inside the scientific environment so the Mac does not need historical R packages. Use a dedicated research container context/profile when implementation starts, preserving other projects' runtimes. Test all requested resource, network and filesystem restrictions against that actual engine. Do not assume a modern CLI means a modern daemon. Use a maintained engine for the eventual worker and explicitly verify AMD64 emulation if the reference image needs it.

Proposed local allocation: a 4-vCPU, 8-GiB VM with 30 GiB disk initially, one 2-vCPU/4-GiB numerical job, and bounded parser/model concurrency. The machine has headroom, but the product should remain usable on a 16-GiB development laptop. Native ARM64 and emulated AMD64 runs are distinct environments; compare them explicitly rather than expecting byte-identical floating-point output.

Colima's installed help supports a named profile, `--cpus`, `--memory`, `--disk`, `--activate=false`, `--mount`, and `--vz-rosetta`. Setup must disable default home mounts and expose only the application's artifact staging directory. Do not start a broad home-mounted VM and call it an untrusted-code boundary. Keep Docker context selection in the supervisor's configuration, not a global shell mutation.

## Setup contract to implement

The following commands are proposed UX, **not commands that exist in this planning-only folder yet**:

```sh
cd '/Users/chris/Projects/science-research-&-reproducibility-platform'
make doctor
make setup
make fixture-verify
make reference-build
make dev
```

`doctor` should inspect available tools and versions, the configured Docker context, free disk, port availability, image architecture support and sandbox policy probes. It must not print environment values, tokens or private endpoints. `setup` should create the dedicated runtime and PostgreSQL volume, apply migrations, install pinned app dependencies and generate local configuration. It should be idempotent and avoid changing unrelated Docker contexts.

Use `127.0.0.1:3000` for the browser app, `127.0.0.1:8000` for the API and a dedicated local PostgreSQL port such as 5433. If a port is occupied, inspect ownership; stop a stale process only when it belongs to this workspace. Never kill an unrelated service merely to keep default ports.

Store operational state under `~/Library/Application Support/ResearchWorkbench/` with mode 700, outside imported repositories. Use subdirectories for staged inputs, content-addressed blobs, attempt scratch, exports and local logs. Model credentials are optional and loaded by the broker from local environment or Keychain; they never enter execution images, exported runs or source fixtures. No production cloud access is needed for the first release.

`fixture-verify` checks manifests without executing scientific code. `reference-build` retrieves only declared dependencies under its own cap and seals the resulting image digest. `dev` starts the API, supervisor and browser app while exposing only loopback interfaces. A ready state means the database is reachable and migrations are current; numerical readiness separately confirms the runner and reference image are available.

## Daily use and demonstration

Open the workspace, select a saved target or add reviewed input files, inspect source/method fields, lock a plan and launch a run. Watch its actual state and logs. When interrupted, reopen the application and inspect recovery status. A draft correction never changes an in-flight run. To change methods, create a new revision and run.

Demonstrate the product in this order:

1. Show the exact paper version and Figure 1 region. Click a filtering parameter to reveal its source and review history.
2. Start a fresh run. Show run ID, image identity, limits and live logs. Use a saved run only if it is visibly labeled.
3. Compare numerical outputs and the figure, including any unavailable reference values. Open the input file and producing code from one selected result.
4. Explain the filtering discrepancy. Run the single allowed variation and show the full retained-set difference and parent relationship.
5. Cancel a deliberately slow safe test job, confirm termination, then demonstrate recovery of another job after a controlled supervisor restart.
6. Export and rerun the sealed bundle in a fresh workspace. Explain which bytes are included, which must be retrieved under their source terms, and what the result does not establish scientifically.

The live scientific run time is not yet measured. Before a presentation, prebuild the environment and verify source availability without fabricating execution. An offline saved example should remain navigable if the network is unavailable, while fresh execution and cached output are clearly distinguished.

## Resource and cost policy

These are planning envelopes in USD, not current provider quotes or measured operating costs. Do not provision cloud services or make paid model calls for this plan.

| Item | Initial policy | Measurement needed |
|---|---|---|
| Data acquisition | 25 MB per declared source by default, 100 MB per workspace import, bounded archive expansion | Actual content size, checksum and access retries; primary count archive is about 2 MB |
| Numerical execution | One concurrent job; 2 vCPU, 4 GiB RAM, 10 minutes, 2 GiB scratch, 64 PIDs | Wall/CPU time, peak RSS, output and disk use on reference image |
| Environment build | 30 minutes and 10 GB disk per strategy; cached sealed image afterward | Native versus emulated build time and dependency sizes |
| Logs/outputs | 10 MB logs per attempt; 100 MB promoted outputs per run initially | Truncation counts, actual export size and whether limits impair diagnosis |
| Optional model work | 2 calls plus one format repair initially, 30k input/5k output tokens total, target $2 per workspace session and $20 monthly developer cap | Actual provider usage, failed calls and explicit price version |
| Storage | 10 GB soft cap; retain accepted references and all scientific attempt metadata; scratch removed after seven days | Blob reuse, orphan growth, export size and user-selected retention |
| Small cloud pilot | Approval/planning ceiling of $150/month for compute, database, storage, backups and model use combined | Obtain current provider quotes and measured workload before deployment; this is not a promise the architecture fits that price |

Cost formula: `input_tokens * input_price / 1e6 + output_tokens * output_price / 1e6 + tools + compute + storage + egress`. Reserve the maximum next-call cost transactionally before dispatch; release/reconcile afterward. Include critic calls, retries and failures. Unknown usage is `unknown`, not zero. Strict-dollar mode must refuse adapters that cannot bound charges; token/wall limits alone do not guarantee a dollar cap.

The deterministic local slice incurs no model API charge and no necessary cloud bill, excluding electricity and existing hardware. Prebuilt images and scientific outputs need storage even when idle. Cloud estimates must account for always-on database/API resources, backups and egress, not just seconds spent running R.

## Observability and operations

Use correlation IDs for workspace, run, attempt and source ingestion. Record queue age, stage duration, success/failure class, retries, lease expiry, cancellation latency, artifact integrity failures, cache hits, model usage completeness and resource maxima. Log state transitions and safe error classes, with bounded scientific stdout/stderr stored as protected artifacts.

OpenTelemetry spans cover ingestion, parsing, model calls, execution and comparison. Export identifiers and metrics by default, not paper text, filenames containing private information, data rows, full prompts or credentials. Distinguish infrastructure health from numerical disagreement: a mismatch is not an incident unless the system misreported or lost evidence.

Back up PostgreSQL and referenced artifacts together using a manifest that identifies the logical backup point. Test restoration into a fresh workspace, validate blob digests and ensure unfinished jobs reconcile safely without rerunning external effects. Add simple maintenance tools for stuck jobs, orphan attempts, storage usage, failed exports and schema migrations. No operator action should silently edit an accepted result.

## Path to research-team production

| Stage | Added capabilities | Gate |
|---|---|---|
| Personal local | One owner, loopback API, curated recipes, local durable state and artifacts | Recovery, cancellation, resource controls and export rerun verified |
| Small team pilot | OIDC, owner/editor/reviewer/viewer roles, HTTPS, project-scoped queries, remote Linux workers and object storage | Actual repeated user workflow; cross-workspace tests; backups restored; secrets isolated |
| Production team service | Separate worker/control hosts, reviewed image registry, durable orchestration where justified, quotas, audit export, monitoring and retention | Workload/isolation tests, dependency patch process, restore/incident drills and measured capacity |
| Broader untrusted service | Strong disposable sandbox boundary per workload, tenant-aware scheduling/cache/storage, hardened source acquisition | Independent security assessment and adversarial tenant tests; no reliance on container names or prompts for isolation |

Editors propose and run plans within quotas; reviewers accept scientific records; owners manage membership and retention; viewers inspect only. A later policy may require a different person to review a changed analysis, while personal mode records self-review honestly. Authorization is derived from authenticated membership and enforced on every request, event stream, object read, export and cache lookup. UUID secrecy is not access control.

Use append-only review/audit events and an external audit sink only when team requirements justify it. Protect artifacts in transit and at rest; scope worker credentials to one run's staging area and expire them. Separate build-network access from no-network computation. A multiuser launch must not expose the developer's local daemon to the internet.

Production release work is outside this planning task. A future release should follow the repository's process, apply backward-compatible migrations before dependent code, verify actual service revisions and database state, and run focused health checks. Preserve in-flight plan/recipe versions across upgrades. Prefer additive changes and rollback of code that can still read the new schema; ask before destructive or data-deleting migrations.

## Learning milestones

| Build stage | Concepts to explain without assistance | Independent exercise | Interview/system-design explanation |
|---|---|---|---|
| P0 fixture | Count matrices, library size, CPM/log-CPM, filtering, sample metadata, original versus adapted analysis | Calculate CPM for a tiny hand-built matrix; change one count and predict whether filtering changes | Why reproducibility needs data, code, environment and a defined target; why a matching plot is insufficient |
| P0 reference | Package locks, image digests, CPU architecture, floating-point tolerance | Rebuild from declared inputs, inspect `sessionInfo()`, diagnose one missing package and preserve the correction | Why containers help but do not guarantee reproducibility or security |
| P1 persistence | Transactions, unique constraints, optimistic concurrency, leases and fencing | Submit the same request twice; kill the worker after container creation; trace how recovery avoids duplicate acceptance | At-least-once work versus exactly-once acceptance; database/external-effect boundary |
| P1 sandbox | Processes, signals, stdout/stderr, namespaces, mounts, resource limits | Run a safe infinite loop and output flood in the disposable test runner; confirm cancellation and log caps | Why no credentials or network go into scientific code, and what the supervisor is trusted to do |
| P2 browser | Async state, SSE replay, typed APIs, URL state, accessibility | Disconnect the browser mid-run; repair one event replay or stale-cache UI bug | Why the browser is not the job owner; how to keep a result inspectable after reconnect |
| P2 provenance | Content addressing, DAGs, source geometry, revisions, artifact retention | Manually trace one displayed number to its input file and code; correct one source region | How a method change invalidates future comparisons while preserving historical evidence |
| P3 assistance | Retrieval, structured outputs, abstention, prompt injection, evaluation leakage | Write five adversarial extraction cases and compare lexical/manual results with one assistant | Why more agents may worsen cost and correlated errors; what evidence would justify a critic |
| P4 scientific depth | Design matrices, confounding, paired analyses, multiple testing, effect sizes | Fit a tiny model with and without a blocking variable and explain the change; identify a reversed contrast | Computational agreement versus scientific validity; why a failed rerun is not a refutation |
| P5 team operations | Authorization, isolation, migrations, budgets, backups and observability | Restore a backup, test a forbidden artifact read, and diagnose a failed migration in a disposable environment | Evolution from local modular system to remote workers without premature services or Kubernetes |

For each milestone, keep a short personal explanation and one debugging note recording what failed, how it was located and why the fix works. Demonstrate competence by making a small change without assistance and explaining the observed consequences. Do not memorize architecture vocabulary or claim operational scale that has not been exercised.
