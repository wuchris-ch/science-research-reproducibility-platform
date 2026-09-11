# Granular commit plan

[Start](../README.md) · [Implementation backlog](IMPLEMENTATION.md)

## Working convention

Build a robust history with many small, meaningful commits throughout implementation. Commit when a coherent change is complete and its relevant checks pass. The history should explain how the system became useful, where problems appeared, and why corrections were made. Keep actual debugging fixes and experiments that produce durable knowledge as distinct checkpoints.

The outline below contains 60 intended checkpoints across the staged product. It is a guide to decomposition, not a quota: split a change further when it contains independently reviewable behavior, and combine tightly coupled changes when splitting would leave an unusable intermediate state. Do not add empty commits, artificial file-by-file fragments, backdated history or fabricated test results. Every commit should make sense to a reviewer who did not see the conversation.

This remains a planning-only task. No commits, repository initialization, pushes or deployments are authorized by this document itself. During implementation, make frequent local checkpoints within the authorized workflow; publish them only under the applicable authorization and repository process.

## Checkpoints

| # | Suggested commit subject | Coherent scope |
|---|---|---|
| 1 | `docs: define reproduction workbench scope and user workflow` | Product decision, boundaries and first workflow |
| 2 | `docs: record source-backed demo feasibility` | Paper/version, artifact manifest, probe and limitations |
| 3 | `docs: specify execution and provenance contracts` | Architecture, state, API and trust boundaries |
| 4 | `docs: define delivery and verification gates` | Backlog, evaluation, operations and learning plan |
| 5 | `chore: scaffold scientific fixture tooling` | Minimal dependency files, paths and documented entrypoint |
| 6 | `feat: verify source archives against sealed manifests` | Bounded acquisition and byte integrity checks |
| 7 | `feat: validate RNA-seq counts and sample identity` | Count schema, nine-sample map, exact input invariants |
| 8 | `docs: align the published figure with source methods` | Inspected PDF/JATS regions and target contract |
| 9 | `build: define the reference R environment` | Reviewed dependency inventory, build policy and image identity |
| 10 | `feat: implement the reviewed density figure recipe` | Source-preserving adapter and explicit patch |
| 11 | `feat: capture numerical outputs and execution receipts` | Arrays, plot, session information and run identity |
| 12 | `test: verify the reference recipe and fresh reruns` | Meaningful scalar and consistency checks |
| 13 | `feat: add the controlled filtering variation` | One parameter-policy delta and retained-set comparison |
| 14 | `docs: record reference compatibility findings` | Actual observed successes, failures and adaptations |
| 15 | `chore: scaffold the typed control API` | FastAPI structure, health response and error contract |
| 16 | `feat: persist workspaces and source versions` | First migration, identity constraints and source records |
| 17 | `feat: store immutable method and plan revisions` | Revision model and correction history |
| 18 | `feat: enforce reviewed plan locking` | Required evidence, unresolved fields and immutable locks |
| 19 | `feat: add content-addressed artifact storage` | Safe storage interface and digest verification |
| 20 | `test: cover interrupted artifact promotion` | Crash points, orphan handling and invalid references |
| 21 | `feat: submit durable idempotent runs` | Transactional run/job/event creation and conflict semantics |
| 22 | `feat: claim jobs with fenced attempt ownership` | Claims, epochs and lease state |
| 23 | `feat: launch constrained scientific containers` | Narrow supervisor interface and fixed recipes |
| 24 | `feat: collect and validate sandbox outputs` | Safe paths, bounded artifacts and schema checks |
| 25 | `feat: reconcile attempts after supervisor restart` | Container intent/name/ID reconciliation |
| 26 | `feat: cancel runs with verified termination` | Persisted cancellation, grace period and stop confirmation |
| 27 | `feat: enforce execution resource budgets` | Time, memory, process, disk and output policy |
| 28 | `test: exercise lease expiry and cancellation races` | Stale acceptance and competing-worker regression cases |
| 29 | `feat: stream persisted run events` | SSE replay and event cursor behavior |
| 30 | `feat: expose bounded logs and run diagnostics` | Operational inspection and visible truncation |
| 31 | `feat: generate the browser API client` | Versioned OpenAPI-to-TypeScript contract checks |
| 32 | `feat: build the research workspace shell` | Navigation, responsive layout and selected-result state |
| 33 | `feat: display source passages and figure regions` | Source viewer and verified geometry |
| 34 | `feat: review and correct extracted method fields` | Origin/gap labels, correction form and conflict handling |
| 35 | `feat: display live execution and cancellation state` | Real API integration and reconnect-safe UI |
| 36 | `feat: compare published and regenerated results` | Numerical observables, limits and separate outcome labels |
| 37 | `feat: navigate result evidence lineage` | Number-to-artifact-to-input inspection |
| 38 | `feat: create reviewed variations from locked plans` | Parent links, allowed delta and new-run workflow |
| 39 | `feat: export reproducible result bundles` | Manifest, rights-aware files and rerun instructions |
| 40 | `test: verify exported bundles in a fresh workspace` | Independent import/rerun and integrity verification |
| 41 | `fix: resolve review accessibility and layout defects` | Actual defects discovered by keyboard and viewport review |
| 42 | `test: cover the complete live research workflow` | Selection, review, run, discrepancy, variation and export |
| 43 | `feat: add an optional model broker with usage limits` | Scoped inference, credentials and reservations |
| 44 | `feat: propose source-linked structured methods` | Single-assistant extraction contract and abstention |
| 45 | `test: reject unsupported extraction and injected instructions` | Critical-field and capability-boundary tests |
| 46 | `eval: add versioned extraction and alignment cases` | Corpus definitions and independently reviewed labels |
| 47 | `eval: compare assisted review with the simpler baseline` | Actual paired measurements and failure analysis |
| 48 | `feat: add a method critic when evaluation supports it` | Conditional role addition, separate context and budget |
| 49 | `feat: support a locked differential-expression contrast` | One full DE workflow with declared design and universe |
| 50 | `test: verify contrast direction and multiple-testing semantics` | Scientific error cases beyond plot agreement |
| 51 | `feat: add a second paper and dataset adapter` | Independent input family instance and honest support limits |
| 52 | `feat: review bounded analysis-code patches` | Original/altered code identity and fresh verification |
| 53 | `security: isolate untrusted analysis execution` | Tested stronger worker boundary before broader uploads |
| 54 | `feat: add team identity and workspace membership` | Authentication and scoped authorization |
| 55 | `feat: enforce workspace isolation across artifacts and jobs` | Query, stream, export and cache boundaries |
| 56 | `feat: record team review and audit events` | Roles, revision acceptance and attributable actions |
| 57 | `ops: add backup and restoration procedures` | Consistent database/artifact backup and tested restore |
| 58 | `ops: introduce remote workers with reconciled ownership` | Measured deployment need and preserved contracts |
| 59 | `test: exercise team isolation and recovery failures` | Adversarial workspace and remote-worker cases |
| 60 | `docs: document measured capabilities and remaining limits` | Accurate release evidence, operating guide and demonstration |

Checkpoint 41 is an example of a real correction commit, not a request to invent a defect. Checkpoints 48 and 53-59 depend on the product and evaluation gates; they may be deferred or replaced by evidence-based decisions. If historical-environment work uncovers several independent compatibility issues, preserve each diagnosed fix and its regression check as additional commits.

## Commit quality

Use concise subjects that name changed behavior. Add a body when the reason, tradeoff or validation is not obvious. Include the meaningful check and result, with a limitation when the work was only inspected. Keep migrations with their compatible application change or sequence them so each committed state remains valid. Keep lockfiles with the dependency changes that require them.

Before committing, inspect the diff, untracked files and staged content. Exclude downloaded datasets, large images, local databases, secrets, private endpoints and transient logs unless a small fixture is deliberately approved for versioning and its terms permit it. Never add signatures, generated-by notices, AI attribution or co-author lines. Do not use `codex/` branch prefixes.

Use feature branches organized around coherent backlog units. Prefer a merge policy that preserves useful implementation commits. If repository policy requires squash merges, keep the feature-branch history available as appropriate and use smaller PRs so the main branch still records meaningful changes. Do not rewrite shared history without explicit authorization. The aim is a truthful engineering record that can be read, tested and debugged commit by commit.
