# Source-to-sensitivity study milestone

Research Workbench 0.2 adds executable uploaded studies and a portable sensitivity explorer. The demonstration uses Love, Anders, Kim and Huber's 2015 version-1 RNA-seq workflow, with the historical airway 0.102.0 count matrix and four paired human donors. This is the DESeq2 workflow reanalysis, not a rerun of the original Himes differential-expression pipeline.

[Public explorer](https://research-workbench-airway.chrisw21tech.chatgpt.site) · [Replay bundle](https://github.com/wuchris-ch/science-research-reproducibility-platform/releases/download/v0.2.0/airway-sensitivity.zip) · [Execution receipt](../evidence/airway-study-verification.json)

## Reproduce the walkthrough

1. Run `make setup`, `make serve` and `make worker` as described in the README. Setup registers both scientific runtime identities.
2. Create a workspace. In **Onboard a study**, upload the versioned paper PDF, JATS supplement, sample annotation supplement, count matrix and sample table. The pinned source and data identities are in `fixtures/paper-assets.json` and `fixtures/airway-data.json`.
3. Deliberately replace sample `SRR1039521` with `SRR1039599` in the sample table. Validation rejects the missing/extra pair. Restore the correct table and validate again. In the recorded demonstration the failed check is revision 7 and the corrected validation is revision 9.
4. Review all six method decisions: organism, count scale, donor-adjusted design, treated/control contrast, paired experimental units and minimum total count. Link each decision to its source region and record the mapping rationale. The recorded graph contains 2,220 regions from the paper and supplements. The minimum-count decision links to the exact expression on PDF page 14.
5. Seal the onboarding record, create an analysis plan, inspect the generated methods and lock it. Counts and sample identities are immutable. Compatible uploaded studies use the registered adapter without adding a dataset branch to the statistical recipe.
6. In **Sensitivity studies**, register the full matrix below with alpha 0.05 and minimum absolute log2 fold change 1. Start the family, inspect every terminal outcome, filter the gene table and compare effects with donor-level normalized counts.
7. Export the family. Open `study.html` offline, verify with `python3 reproduce_study.py --verify-only`, then rebuild and replay a variant in a fresh directory with `python3 reproduce_study.py --variant 1 --context colima-research`.

## Frozen choices and actual outcomes

The family was frozen before any variant ran, after the initial reference result was available. This is an internal recorded analysis family, not an external preregistration or an independent discovery cohort. All eight variants use the same input bytes, adapter version, immutable runtime and resource limits. The worker persists submission and cancellation state, resumes after interruption and retains failed or unsubmitted outcomes.

| Variant | Minimum total count | Size factors | Independent filtering | Retained genes | Significant at within-run BH 0.10 |
|---|---:|---|---|---:|---:|
| 1 | 2 | ratio | yes | 29,391 | 4,822 |
| 2 | 2 | poscounts | yes | 29,391 | 4,714 |
| 3 | 10 | ratio | yes | 22,369 | 4,846 |
| 4 | 10 | poscounts | yes | 22,369 | 4,865 |
| 5 | 2 | ratio | no | 29,391 | 4,230 |
| 6 | 2 | poscounts | no | 29,391 | 4,155 |
| 7 | 10 | ratio | no | 22,369 | 4,567 |
| 8 | 10 | poscounts | no | 22,369 | 4,599 |

All eight completed. The complete input universe contains 64,102 genes, including 30,633 all-zero rows. The family correction covers 512,816 gene-variant hypotheses using Benjamini-Yekutieli, assigning P=1 to missing tests. A gene is family-supported only when every planned run completed, every variant estimates it, signs agree, the minimum effect is reached and every family-adjusted P passes alpha. **660 genes meet this rule.** Incomplete families cannot receive that classification. Approximate pointwise 95% coefficient intervals are shown separately from this family criterion.

The reference retained 29,391 genes, matching the source. It called 4,822 significant genes versus 4,897 reported, with 2,617 up and 2,205 down versus 2,647 and 2,250. R 4.2.2 / DESeq2 1.38.3 replaces the paper's R 3.2.1 / DESeq2 1.8.1. Filtering and numerical fitting differ between versions. The report preserves the discrepancy, twelve independently published gene-effect examples, Figure 10 from PDF page 25, and each numerical artifact hash.

An independently extracted reference bundle and a separately extracted family-variant bundle rebuilt their runtimes. Each replay reproduced all six numerical files byte for byte: metrics, design, genes, samples, effects and normalized counts. Image identities changed with build metadata; numerical identity was verified directly. The receipt preserves both identities and every comparison.

## Extraction benchmark

The held-out fixture freezes eighteen source questions, evidence anchors, expected answers and an exact scorer before model calls. It covers Himes, Schurch and Holik papers, including primary versus pilot experiments, sample exclusions, method-specific normalization and unsupported details requiring abstention. Himes was already a scientific source for the project; these questions were excluded from lexical-development fixtures.

| Evaluation | Lexical baseline | Configured extraction model |
|---|---:|---:|
| Frozen exact scorer | 12 / 18 | 15 / 18 |
| Separate source-based semantic adjudication | 12 / 18 | 18 / 18 |

Three model answers failed literal matching but were scientifically equivalent to the gold: version-qualified Cuffdiff and TopHat names, and “Median ratio method.” The original strict scores and responses are retained alongside the source-based adjudication. The same reviewer created the gold and adjudicated equivalence; a blinded second reviewer and participant review-time experiment have not been run.

The benchmark made exactly three calls, using 11,132 input and 1,182 output tokens, with about 18 seconds of model-call elapsed time. It enforced call, input, output and time bounds. Invoice cost was unavailable, so no dollar cost is asserted. No additional model critic was added without a measured same-budget benefit. All application proposals still require human method review. [Frozen fixture](../fixtures/extraction-heldout.json) · [Measured results](../evidence/heldout-extraction.json)

## Release and operating scope

The public example is a static read-only report containing actual study outputs. GitHub provides the replay archive; Sites serves the explorer. The application API and worker remain the local execution profile. A separately configured authenticated team deployment still requires its own infrastructure, identity-provider and database verification.

The registry accepts typed bounded scientific choices, not uploaded executable code. Parsing, count validation and container execution have separate bounds. API and PostgreSQL contracts, the production interface build, the deployable API image, interrupted staging recovery, negative family criteria, real scientific runs and cold replays provide distinct evidence for these boundaries.
