# Repository reuse assessment

> Design record from the planning phase. See [implemented behavior and evidence](IMPLEMENTED.md) and the [current operating guide](RUNBOOK.md) for delivered capabilities and remaining gates.

[Start](../README.md) · [Architecture](ARCHITECTURE.md) · [Inspection receipts](../evidence/repository-inspection.json)

## Inspection boundary

Source inspected September 11, 2026. These are static observations and bounded reasoning about control flow, not claims that repository tests or deployed systems passed. No files in these repositories were changed. Hashes in the inspection receipt identify the specific files because other tasks may continue editing them.

| Repository | Inspected HEAD | Working-tree observation |
|---|---|---|
| CodeTrace | `e0b436028a7c67e2a431a40ba117e7e3ee230a71` | Clean at initial inspection |
| DSPy-Supabase-RAG | `85a5d7e6abf47d1b93feccdaa1c2e0d3f13a0a5b` | Untracked browser artifacts present; untouched |
| distributed-task-scheduler | `71af5c702fd306e2683d13569776de59a857e53f` | Modified `docker-compose.yml`; untouched |
| agent-eval-k3s | `9b68ab520427e93a104a8d36966401a499f2fd92` | Untracked Finder metadata; untouched |
| pr-review-agent-flue | `024f477e613de41a23a4b6a8986c735f703bbdae` | Clean at initial inspection |
| multi-agent-software-engineering-platform | No Git repository at inspection | Planning documents and source already present; README's “no application” statement was stale relative to the directory contents |

The career task's metadata was accessible, but its recent message bodies were not returned. The project brief supplies the career goals; no additional conclusions are attributed to unseen conversation history.

## CodeTrace: strongest source for interaction and evidence patterns

Observed in [spatial-pdf.ts](/Users/chris/Projects/codetrace/lib/spatial-pdf.ts): page/text-item identities, normalized top-left regions, extraction methods, and explicit uncertain or missing-information outcomes. Its classifications and defaults are tailored to building drawings. Preserve the coordinate and evidence concepts, replace the document ontology, and impose smaller scientific-paper limits.

[validate-output.ts](/Users/chris/Projects/codetrace/lib/ai/validate-output.ts) checks requested-field coverage, duplicate fields, type/unit compatibility, page ranges, existing text IDs, overlapping evidence regions, and rendered-view receipts tied to source hashes. This is real validation code, not just a README promise. It does not prove that a cited passage entails a scientific interpretation. Adapt its checks into the new typed extraction boundary and add table-cell, panel, statistical-method and version matching tests.

[revision-evidence.ts](/Users/chris/Projects/codetrace/lib/revision-evidence.ts) removes stale evidence when facts change. The corresponding [tests](/Users/chris/Projects/codetrace/tests/revision-evidence.test.ts) cover replacement and manual edits. Preserve old scientific revisions and create new edges rather than deleting historical provenance. A changed contrast, sample mapping or filter invalidates comparisons derived from it.

[worker.ts](/Users/chris/Projects/codetrace/lib/ai/worker.ts) verifies source hashes, writes spatial/document maps, heartbeats jobs, validates candidates and classifies retries. [local-queue.ts](/Users/chris/Projects/codetrace/lib/ai/local-queue.ts) uses file records and lock ownership. Reuse stage vocabulary and inspection UX, not the queue implementation: separate reads and writes, heartbeat writes and stale-lock cleanup need concurrency analysis before any multi-worker claim. The new application uses transactional job state and fenced attempts.

**Decision:** port small concepts with new scientific tests. Do not copy the domain application, compliance rules, worker prompts, or local provider configuration. No top-level LICENSE file was found in the initial file inventory; establish ownership and dependency notices before redistributing copied code. This does not prevent implementing the same general patterns independently.

## Medical RAG: retrieval ideas, not evidence authority

[retriever.py](/Users/chris/Projects/DSPy-Supabase-RAG/retriever.py) implements vector retrieval, keyword/BM25 paths, reciprocal rank fusion and optional rerankers. This can inform later cross-document methods retrieval. A single curated paper does not need an embedding database: start with section selection and lexical search, measure retrieval misses, then add hybrid search if it improves held-out performance.

[pdf_processor.py](/Users/chris/Projects/DSPy-Supabase-RAG/pdf_processor.py) uses Docling but exports Markdown and chunks it. `DocumentChunk.page` exists, yet the examined chunk-building paths do not populate a page locator; table and bounding-box structure is not retained in the chunk contract. `ocr_used` is populated from a configuration flag, not observed per-page OCR use. Therefore it is not a drop-in multimodal evidence layer. The fixed-size chunk loop also computes `start = end - overlap` without an end-of-document break, a static indication of nontermination for some positive-overlap inputs. Do not reuse that loop without a focused regression test.

[faithful_rag.py](/Users/chris/Projects/DSPy-Supabase-RAG/faithful_rag.py) extracts and verifies claims using model calls. That is a useful advisory pattern; the same model family checking an answer is not independent scientific validation. The new system obtains numerical results from execution artifacts, and uses a separately maintained reference evaluator.

[supabase_schema.sql](/Users/chris/Projects/DSPy-Supabase-RAG/supabase_schema.sql) contains an unrestricted RLS policy and no workspace membership model. It is unsuitable for team isolation. No deployment was checked. No top-level LICENSE file was found in the initial inventory.

**Decision:** use lessons about retrieval, strict claims and evaluation, but build a smaller document pipeline that preserves JATS/PDF structures. Keep generated context separate from source text. Do not inherit the Streamlit app, database schema or provider integrations.

## Distributed scheduler: concrete gaps to avoid

| Source evidence | Observation | Failure scenario and new design |
|---|---|---|
| [API enqueue](/Users/chris/Projects/distributed-task-scheduler/internal/api/server.go) | PostgreSQL creation commits before Redis enqueue; idempotent resubmission skips enqueue | Crash between stores can strand a job. Use one PostgreSQL transaction for business record, job and event. |
| [Redis queue](/Users/chris/Projects/distributed-task-scheduler/internal/queue/redis_queue.go) | Initial pop/lease is Lua-atomic; promotion/reclaim reads IDs before a later pipeline | Two reclaimers can observe the same IDs. New claims use row locks and a monotonically increasing attempt epoch. |
| [Processor](/Users/chris/Projects/distributed-task-scheduler/internal/worker/processor.go) | Reads cancellation before execution; then acknowledges and marks success without a final state guard | Cancellation during execution can be overwritten by success. Persist cancellation and condition terminal acceptance on the current epoch and state. |
| [Processor](/Users/chris/Projects/distributed-task-scheduler/internal/worker/processor.go) | No general handler heartbeat; default simulated handler extends once and sleeps | Long custom handlers can outlive leases. Supervisor renews leases independently and reconciles actual containers. |
| [Store](/Users/chris/Projects/distributed-task-scheduler/internal/store/postgres.go) | Status updates key only on job ID; no attempt token in update predicate | Stale workers may write terminal state. Use compare-and-set state/version and attempt fencing. |
| [Store/API](/Users/chris/Projects/distributed-task-scheduler/internal/store/postgres.go) | Idempotency key lookup is global; shown job reads/cancels lack tenant-scoped predicates | Do not expose as a shared service. Scope idempotency and every lookup to authenticated workspace identity. |

These failure scenarios follow from examined code paths; they were not injected into a live system. Retry jitter, audit events and queue metrics are useful ideas. Repairing the scheduler is separate work and must not gate this product. No top-level LICENSE file was found in the initial inventory.

## Evaluation and review projects

[agent-eval-k3s blackbox models](/Users/chris/Projects/agent-eval-k3s/src/agent_eval/blackbox/models.py) have versioned suites, strict JSON validation, input digests, observations and evaluator-only context. [Targets](/Users/chris/Projects/agent-eval-k3s/src/agent_eval/blackbox/targets.py) support command and HTTP boundaries with size and time limits. The [agent protocol](/Users/chris/Projects/agent-eval-k3s/src/agent_eval/agents/base.py) has command-building and transcript parsing for supported coding agents. This does not mean a scientific workbench adapter or numerical/region-IoU grader exists today.

**Decision:** keep that project an optional independent consumer of exported candidate observations. Add a versioned JSON command or HTTP adapter there when authorized in a future task. Its existing exact-match/JSON-subset metrics can cover structured outputs; domain numerical and geometry checks need explicit extensions. The workbench must still run and test independently. Do not copy hidden cases into model prompts or use its secrets in experiment containers. Apache-2.0 was verified in its LICENSE.

[Flue runner](/Users/chris/Projects/pr-review-agent-flue/src/runner.ts) bounds agent messages, output and timeout; [schema.ts](/Users/chris/Projects/pr-review-agent-flue/src/schema.ts) validates hash-bound findings, paths and consistent risk labels. [review.ts](/Users/chris/Projects/pr-review-agent-flue/src/review.ts) supports local diff review. Use as an optional development-time reviewer or later advisory reviewer of explicit analysis-code patches. It cannot validate a statistical conclusion or authorize a scientific result. Keep its watcher, GitHub operations and provider configuration out of the runtime. Apache-2.0 was verified.

## Relationship to the software engineering platform

The inspected [architecture](/Users/chris/Projects/multi-agent-software-engineering-platform/ARCHITECTURE.md) and [contracts](/Users/chris/Projects/multi-agent-software-engineering-platform/CONTRACTS.md) contain useful concepts: sealed candidates, independent verification, fenced attempts, effect reconciliation and budget reservation. They concern repository tasks, patches and publication.

This product concerns paper versions, scientific methods, data matrices, parameters, comparisons and evidence review. Share design principles, not runtime state, databases, workers or release dependencies. A future interface could request a code patch and receive a sealed diff, but the science workbench must decide which scientific checks are required and preserve the distinction between original and altered analyses. No integration is needed for the first usable release.
