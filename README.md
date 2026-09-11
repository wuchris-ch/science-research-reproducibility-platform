# Scientific Research & Reproducibility Platform

Build a **paper-to-result research workbench for reviewing and rerunning published bulk RNA-seq analyses**. Start with processed gene counts, one selected figure, a reviewed analysis plan, isolated execution, and an inspectable comparison. Every result must lead back to the exact source, inputs, code, environment, and execution.

The first example is **Law et al., RNA-seq analysis is easy as 1-2-3, version 3, Figure 1**. A bounded data probe verified the nine input files and independently recovered the reported 16,624 retained genes. This is feasibility evidence, not a completed R reproduction. The complete usable slice adds the original figure, numerical outputs, discrepancy inspection, one controlled filtering variation, and an export.

Research checked September 11, 2026. This folder contains planning documents and inspection receipts only. No product implementation, commits, deployments, or paid experiments were performed.

| Read | Purpose |
|---|---|
| [Product and landscape](docs/PRODUCT.md) | Why reproducibility wins over clinical evidence intelligence, users, competition, scope, UX |
| [Demo selection and feasibility](docs/DEMO.md) | Exact paper/result, verified files, licenses, fallbacks, remaining gates |
| [Architecture and contracts](docs/ARCHITECTURE.md) | Stack, diagrams, state, APIs, provenance, isolation and recovery |
| [Implementation backlog](docs/IMPLEMENTATION.md) | Dependency order, acceptance criteria, exact first task |
| [Commit plan](docs/COMMIT-PLAN.md) | Granular implementation history with meaningful, reviewable checkpoints |
| [Testing and evaluation](docs/VERIFICATION.md) | Scientific checks, agent baselines, held-out cases and failure injection |
| [Operations and learning](docs/OPERATIONS-LEARNING.md) | Mac setup, daily workflow, budgets, team path, learning exercises |
| [Repository reuse](docs/REUSE.md) | Source-level findings and selective reuse decisions |
| [Source register](docs/SOURCES.md) | Primary references, dates, versions and evidence limits |

**Recommended stack:** React/TypeScript with Vite, FastAPI/Pydantic, PostgreSQL, a small durable state machine, content-addressed local artifacts, and a separately supervised Docker runner executing R. Add model assistance after the deterministic workflow works. No dependency on the other planned platforms.

**Start here:** implement task **P0.1, seal and reproduce the Figure 1 reference fixture**, in [the backlog](docs/IMPLEMENTATION.md#p01-seal-and-reproduce-the-reference-fixture). Its first action is to verify the recorded input hashes, then build a bounded R environment and capture real numerical and plot artifacts. Historical environment compatibility, source-to-PDF alignment, and demand beyond teaching remain the main unresolved risks.
