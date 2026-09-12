# Product recommendation

> Design record from the planning phase. See [implemented behavior and evidence](IMPLEMENTED.md) and the [current operating guide](RUNBOOK.md) for delivered capabilities and remaining gates.

[Start](../README.md) · [Demo](DEMO.md) · [Architecture](ARCHITECTURE.md) · [Sources](SOURCES.md)

## Decision

Build an **evidence-linked reproduction workbench**, initially for bulk RNA-seq analyses that start from public gene-count matrices and sample metadata. The unit of work is a selected published result, not an entire paper and not an open-ended scientific question. The output is an inspectable reproduction record that another person can rerun or challenge.

The ambitious destination is a research team's workspace for computational review: ingest papers and supplements, reconstruct a selected analysis, resolve missing details, compare results, review changes, run bounded follow-ups, and export durable evidence. The first version supports a narrow set of R recipes. Arbitrary repositories, raw sequencing, clinical recommendations, novel discoveries, and autonomous research campaigns are outside its initial scope.

This choice exercises useful full-stack engineering: structured document review, typed contracts, SQL transactions, background execution, artifact storage, security boundaries, responsive interaction, and measurable correctness. AI engineering adds extraction and planning whose value can be tested. Biological training helps explain the analysis; the product does not require ophthalmology data or access to patients.

## Primary user and recurring job

The initial user is a research assistant, graduate student, or computational biologist reviewing a published analysis before adapting it to a related project. A secondary user is a lab's computational methods lead reviewing that person's choices. A journal club or methods course provides a realistic early testing environment, but successful classroom use alone would not establish team demand.

The proposed recurring job is: “I want to understand how this result was produced, establish whether I can recover it from the available materials, and see what changes under one justified analysis choice.” Today this often spans a paper viewer, repository, terminal or notebook, package troubleshooting, plots, and informal notes. The proposed improvement is to preserve the relationships between those objects and decisions, not simply put a chatbot beside them.

Published Bioconductor workflows demonstrate executable methods teaching and review; Galaxy and iSEE demonstrate substantial existing demand for accessible computational analysis and exploration. They support the plausibility of the workflow, not willingness to adopt this particular product. No user interviews, usage study, or willingness-to-pay validation has been completed. [Bioconductor workflow](https://bioconductor.org/packages/release/workflows/html/RNAseq123.html), [Galaxy FAIR capabilities](https://galaxyproject.org/fair/), [iSEE interface](https://bioconductor.posit.co/packages/release/bioc/vignettes/iSEE/inst/doc/basic.html).

Before adding team features, conduct five task-based sessions with two trainees, two computational researchers, and one methods lead. Observe an actual paper-to-analysis task; measure time to locate inputs, undocumented decisions, corrections, and whether the exported record helps a second person. Proceed toward a pilot if at least three participants can identify a second real task they would use it for and two return to complete it. These are decision criteria, not achieved results. If users mostly need pipeline launching, support export to established workflow tools instead of competing on execution breadth.

## Comparison with clinical evidence intelligence

| Dimension | Reproduction workbench | Clinical evidence intelligence |
|---|---|---|
| Focused first job | Recover one result and review one variation | Link one trial to publications and detect endpoint or evidence changes |
| Main user | Computational researcher or methods trainee | Evidence reviewer, clinical researcher, medical affairs analyst |
| Hard engineering | Durable execution, evidence lineage, isolation, numerical comparisons | Entity resolution, version diffs, scheduled ingestion, study-level extraction |
| Objective checks | Input integrity and numerical reruns have strong deterministic checks | Record changes can be checked; clinical interpretation remains expert dependent |
| Accessible data | Small public count matrices and open code | Public trial records, with incomplete or restricted full text |
| Principal risk | Environment reconstruction and undocumented methods | Incorrect trial-publication linkage, outcome switching interpretation, incomplete evidence |
| Competitive pressure | Galaxy, Code Ocean, Seqera, notebooks | Elicit and established evidence-review workflows |
| Portfolio fit | Broad software systems plus domain-specific computation | Strong information systems project, closer to an advanced retrieval application |

Choose reproduction as the primary product. Keep clinical evidence reconciliation as an alternative product, not a second tab. A credible clinical MVP would link a small set of NCT records to publications, show versioned endpoint/population differences, and require review of uncertain links. That can be useful, but it weakens focus here and adds another evaluation problem. ClinicalTrials.gov's API is a viable source: a direct version endpoint returned API 2.0.5 and a data timestamp of September 11, 2026. That confirms endpoint access, not complete history coverage or publication linkage. [API documentation](https://clinicaltrials.gov/data-api/about-api), [version endpoint](https://clinicaltrials.gov/api/v2/version).

## Current landscape

Checked September 11, 2026. “Documented” means a provider or project describes the feature. It does not mean its quality or security was independently tested.

| Product or project | Verified source and status | Consequence for this product |
|---|---|---|
| Code Ocean | Compute Capsules document code, data, environment and Docker packaging; shipped service documentation | Packaging alone is not differentiation. Offer evidence review and export, not a capsule clone. [Source](https://docs.codeocean.com/osl-guide/getting-started/what-is-a-compute-capsule) |
| Galaxy | Existing open platform with histories, workflows, sharing and provenance | Do not rebuild its tool catalog. Focus on a published target and paper-to-method discrepancies. [Source](https://galaxyproject.org/fair/) |
| Seqera Co-Scientist | April 30, 2026 launch; current CLI docs describe building, running and debugging Nextflow workflows. Launch post marked always-on agents “coming soon”; do not assume that specific roadmap item shipped | A close competitor. Generic bioinformatics agents are insufficient differentiation. [Launch](https://seqera.io/blog/co-scientist-launch/), [current docs](https://docs.seqera.io/platform-cloud/co-scientist/) |
| Elicit Research Agent | August 4, 2026 announcement describes evidence, analyses and cited outputs via app/API | Clinical synthesis is crowded; model-generated bioinformatics is also competitive. Vendor benchmarks are not independent evidence. [Source](https://elicit.com/blog/introducing-elicit-research-agent) |
| Renku 2 | Current docs describe shared code/data/compute and container sessions; Apache-2.0 | Useful deployment and collaboration reference. Do not attribute legacy provenance features to version 2 without checking them. [Source](https://docs.renkulab.io/en/latest/docs/users/knowledge-base/about/) |
| iSEE / Glimma | Existing interactive exploration and linked plots, with source in Bioconductor | Plot interactivity is already solved. Connect it to source regions, method revisions and run comparisons. [iSEE](https://bioconductor.posit.co/packages/release/bioc/vignettes/iSEE/inst/doc/basic.html), [workflow code](https://bioconductor.org/packages/3.23/workflows/vignettes/RNAseq123/inst/doc/limmaWorkflow.R) |
| Binder / notebooks | BinderHub builds environments and launches notebook sessions | Useful portability model, but a live notebook session is not the product's reviewed result record. [Source](https://github.com/jupyterhub/binderhub) |
| DVC / MLflow | Existing data/pipeline versioning and experiment tracking | Borrow conventions and export when useful. Avoid competing run registries in the first release. [DVC](https://github.com/treeverse/dvc.org/blob/main/content/docs/start/data-pipelines/data-pipelines.md), [MLflow](https://mlflow.org/docs/latest/ml/tracking) |

The defensible focus is **reviewable correspondence between a paper result, its stated methods, an executable recipe, and a real run**, including explicit gaps. This is a product hypothesis, not a claim that no competitor has any equivalent feature. The durable value would be carefully curated supported workflows, good correction tools, trustworthy comparisons, and tested failure behavior.

Three recent research systems inform the destination. Google's Science One announcement, July 30, 2026, explicitly calls it an experimental prototype; its evidence-chain and rerun audit ideas are useful, but its reported performance cannot establish biomedical validity. Google's wearable biomarker framework, August 21, 2026, separates numerical computation from generative reasoning and emphasizes leakage checks and human review. FutureHouse's Robin page was updated May 19, 2026 from a May 20, 2025 original; humans performed the physical experiments. None justifies claiming autonomous clinical discovery here. [Science One](https://research.google/blog/science-one-framework-a-verifiable-autonomous-research-framework-via-chain-of-evidence/), [biomarker framework](https://research.google/blog/an-ai-tool-for-prioritizing-candidate-biomarkers-from-wearable-sensor-data/), [Robin](https://www.futurehouse.org/research/demonstrating-end-to-end-scientific-discovery-with-robin-a-multi-agent-system).

## One complete user experience

1. Open the curated paper workspace. Select Figure 1 and its exact article version. Inspect what the system can and cannot reproduce.
2. Review the nine samples, source counts, filtering rule and expected outputs. Click any extracted field to see its passage, table cell or image region. Correct a field into a new revision.
3. Lock the analysis plan. The UI shows resource limits and remaining ambiguities. Required unresolved fields prevent execution.
4. Run. The workbench displays a real job state, elapsed time, logs and cancellation. Reopening the browser preserves progress.
5. Compare published and regenerated figures. Inspect retained genes, library sizes, density curves, and declared tolerances. A completed job may have a mismatched or unverifiable comparison.
6. Open the version-related filtering discrepancy. Create one prespecified alternative using CPM greater than 1 in at least three samples. Show all outputs and the parameter delta.
7. Export the evidence record, input manifest, code, environment recipe, numerical data, figures, logs, limitations and rerun instructions.

## Review interface

Use a three-pane desktop layout with resizable panels: source at left, selected result and comparison in the center, methods and run details at right. A persistent footer shows the active run, state and cancellation. At narrow widths, preserve the same selected item through Source / Result / Methods tabs.

Source view supports PDF page coordinates, JATS paragraphs, captions, figure panels and code line ranges. Center view switches between published figure, rerun figure, numerical table and difference view. Right view groups **reported**, **inferred**, **user-specified**, and **missing** choices. These labels are visible before locking, not hidden in logs. Review edits show before/after values, reason, evidence and affected downstream runs.

Clickable lineage should answer “where did this number come from?” in one action and show the full chain in a second. Render gene labels and tooltips safely. Use keyboard focus, accessible data tables, non-color status labels, loading/error states, and stable URLs for a result and run. Do not use a generic chat transcript as the main navigation.

## Scope boundaries

The first release accepts the curated figure recipe and user-reviewed count/metadata files conforming to its schema. It may extract candidate methods, but it cannot create arbitrary executable code. It reports support as `supported_recipe`, `needs_mapping`, `missing_inputs`, `unsupported_method`, or `license_review_required`.

Later, add a complete differential-expression result, a second study, and a reviewed code-patch workflow. Only then consider importing arbitrary repositories into stronger sandboxes, multiple collaborators, or hypothesis generation. A robust null finding or a well-documented failed reproduction is a useful outcome. Reproducing the computation does not establish biological truth, causality, generalization, or a treatment effect.
