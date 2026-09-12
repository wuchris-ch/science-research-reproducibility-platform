# Implemented behavior and evidence

Verification date: September 11, 2026. The application and scientific checks below were executed against this repository. The read-only public example is described in [the study milestone](STUDY-MILESTONE.md); the authenticated team deployment remains a separate operating profile. Earlier planning documents remain historical design records.

## Delivered scope

| Backlog | Delivered behavior | Evidence |
|---|---|---|
| P0 | Pinned source archives, counts, sample identity, original paper PDFs and page-8 regions; historical R image; reference and controlled variation | `fixtures/`, `recipes/ADAPTATIONS.md`, `evidence/science-verification.json` |
| P1 | Typed API; SQLite and PostgreSQL schema migration; immutable artifacts; idempotent submit; fenced claims; bounded isolated execution; persisted events, diagnostics and recovery | Contract tests plus real runtime and budget receipts |
| P2 | Responsive paper library, source viewer, method correction/revisions, review locks, live runs, published/generated plots, scalar comparisons, lineage, reviews, fresh reruns and export | Browser walkthrough and independent bundle replay |
| P3.1 | Optional HTTPS model broker, structured extraction, source quote validation, server-held credentials, spending reservations and manual workflow | Broker contract tests and three bounded live extraction calls against frozen source questions |
| P3.2 | Versioned lexical baseline evaluation on eight synthetic cases, including misleading instructions and abstention | `evidence/extraction-evaluation.json`; precision 0.8, recall 1.0 within this small set |
| Study milestone | Validated adapter registry, paper/supplement onboarding, paired human DESeq2, frozen sensitivity families, gene exploration and portable offline reports | `evidence/airway-study-verification.json`, `evidence/heldout-extraction.json`, [walkthrough](STUDY-MILESTONE.md) |
| P4.1-2 | Full primary-data differential expression and second-paper MDS adapter | Actual executions, complete tested universe, table validation and package/session records |
| P5 foundations | OIDC access-token verification, workspace roles, scoped queries/storage access, audit, review records, quotas, backup/restore, Docker-engine-bound recovery | Cross-workspace, JWT, restore and recovery tests; isolated PostgreSQL suite |
| Operations | Source checkout lifecycle commands, contract regeneration, CI, API image with no Docker CLI/socket, team configuration template | Build and container health/UI smoke test |

## Measured scientific results

The Law reference contains 27,179 genes across nine samples. The run recovered all nine independently checked library sizes, 5,153 all-zero genes and the reported 16,624 retained genes. The stricter `CPM > 1` in at least three samples retained 14,165. Both raw and filtered density grids, sample summaries and retained IDs are exported.

The differential-expression adapter uses TMM normalization, voom, `~0+group+lane`, the Basal-minus-LP contrast, empirical Bayes, and Benjamini-Hochberg adjustment across all 16,624 tested genes. The observed default result has 9,511 genes at FDR 0.05. This is an observed adapter result, not an independently verified published DE table or the later TREAT analysis. The output validator checks the full universe, finite values, P-value ranges, BH adjustment and declared significance threshold.

The Chen adapter uses org.Mm.eg.db 3.3.0 annotation and recovers 26,357 annotated genes and 15,653 after the declared filter, across 12 samples. It emits MDS coordinates, distances and a plot. Its R 3.5.1 / edgeR 3.24.0 / limma 3.38.3 Linux runtime differs from the paper's R 3.3.1 / edgeR 3.14.0 / limma 3.28.6 Windows environment. Coordinate signs and graphics rendering are not asserted to match exactly.

The Law image uses the declared R 3.5.1, edgeR 3.24.0, limma 3.38.3, RColorBrewer 1.1-2, Rcpp 1.0.0, locfit 1.5-9.1 and jsonlite 1.6. The base digest and package hashes are pinned. Every run records the image identity it actually used. Rebuilding can change the top-level image identity because build attestations include metadata; fresh numerical comparison is therefore recorded separately.

Neither article supplies an authoritative machine-readable density grid or full figure-coordinate table. Matching declared scalars and matching our own reruns does not establish exact numerical agreement with every published figure or scientific conclusion. The UI states this next to the comparison.

## Verification receipts

- `evidence/airway-study-verification.json`: rejected sample mismatch, frozen protocol, all eight executed variants, numerical artifact hashes, and independent reference and family-variant replay receipts. Both replays matched all six numerical files.
- `evidence/heldout-extraction.json`: frozen exact scores, separate semantic adjudication, source links, three-call token/time usage and recorded failures.
- `evidence/staging-recovery.json`: real interruption after input files became read-only, followed by successful idempotent restaging.
- `evidence/science-verification.json`: five real executions, comprising the reference twice, filter variation, differential expression and Chen MDS. Contains run IDs, input/runtime provenance, metrics and numerical consistency results.
- `evidence/export-replay.json`: cold replay from an independently extracted bundle. Verified metrics, density, gene and sample files were byte-identical to the exported run.
- `evidence/runtime-verification.json`: observed no-network execution, read-only root, non-root user, dropped capabilities, bounded memory/processes/tmpfs, denied outbound request and root write, and cancellation after verified termination.
- `evidence/budget-verification.json`: actual timeout and OOM faults in temporary trusted test images, each failed on its first attempt and removed its container.
- `evidence/postgres-verification.json`: contract suite against PostgreSQL 16 with a separate temporary database per test. SQLite-specific backup behavior is tested separately.
- `evidence/api-image-verification.json`: actual API image starts, queries its database, serves the UI, runs non-root with a read-only root, and has neither a Docker CLI nor socket.
- `evidence/extraction-evaluation.json`: the small lexical evaluation preserves failures and its limited scope. A misleading accession instruction still produced a false proposal. Evidence linkage alone does not guarantee semantic correctness.
- `evidence/browser-verification.json`: observed UI actions and responsive/keyboard checks, recorded separately from automated tests.

The Python tests exercise stale revision rejection, unresolved locks, concurrent idempotency, stale-owner fencing, recovery after intent and sealed receipts, daemon failure during cancellation, inaccessible runtime ownership, invalid artifact collection, hash corruption, source boundaries, CSRF, OIDC validation, cross-workspace access, membership, review persistence, spending reservations, uploaded PDF boundaries, chunked request limits and database health failure. Frontend checks compile the generated contracts and production bundle. Two upstream test-client deprecation warnings remain; the suite passes.

## Deliberate changes to the plan

The local profile uses transactional SQLite to make the complete loop usable without another service. PostgreSQL remains supported and directly tested, with advisory locking for schema migration and row locking for worker claims. A small durable supervisor owns scheduling; introducing Temporal now would duplicate that responsibility without measured benefit.

Code changes are released through the repository and rebuilt as a new immutable runtime. The application exposes typed scientific variations, not arbitrary R patches. P4.3 remains gated because the local Docker boundary has not been certified for hostile user code. Uploaded source documents remain inert. Validated paired count inputs can execute through the registered DESeq2 adapter after source review and plan locking.

P3.3's independent critic is not enabled. There is no measured comparison showing that it reduces critical review errors enough to justify cost. The live extraction benchmark covers 18 frozen questions from three source papers: the lexical baseline scores 12/18 and the configured model 15/18 under the frozen exact scorer. A separate source-based semantic adjudication accepts three equivalent model answers, yielding 18/18. Original answers and strict scores are preserved. The same reviewer authored the gold and performed adjudication; no participant review-time study or blinded second review was conducted.

P5 includes tested team foundations and a deployable API image, but no actual authenticated team pilot, managed object storage, or remote-host failover drill was performed. The public release serves a static study explorer; it does not expose the execution API. Workers can share PostgreSQL and a private POSIX artifact directory. An in-flight attempt stays attached to its Docker engine; a different engine cannot declare its container absent and duplicate execution. Cross-engine failover requires explicit operational recovery, not automatic ownership transfer.

## Known operating limits

The fixture cache and artifact directory are private operator-managed storage. Content hashes detect byte changes; they are not cryptographic proof of publisher authorship. Exported bundles may contain workspace events and reviews and should be shared intentionally. Existing immutable artifacts are verified on read; no automatic garbage collector deletes data.

Queued/active jobs are capped per workspace, each execution has declared resource limits, imports are capped at 10 MB including request overhead, and model calls reserve from a workspace budget. Aggregate disk quotas and organization-wide rate limiting are not implemented. Before a multi-tenant deployment, supply those controls at the infrastructure layer and validate them against the intended workload.

The application currently accepts an OIDC access token pasted into its sign-in form. It validates issuer, audience, RS256 signature, issue/expiry claims and subject. It does not yet implement an interactive authorization-code flow. No live identity tenant is configured in the checked-in files.
