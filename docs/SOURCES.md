# Source register

> Design record from the planning phase. See [implemented behavior and evidence](IMPLEMENTED.md) and the [current operating guide](RUNBOOK.md) for delivered capabilities and remaining gates.

[Start](../README.md) · [Product](PRODUCT.md) · [Demo](DEMO.md) · [Repository evidence](REUSE.md)

Sources were checked September 11, 2026. Publication dates below come from page/article metadata, not search-engine “crawled” dates. Mutable documentation is identified as such. Official documentation establishes intended behavior; local observations and source inspection establish only the specific things inspected. No vendor's performance or security claim was independently benchmarked.

## Product landscape and research systems

| Publisher | Source and date/version | Use and evidence limit |
|---|---|---|
| Google Research, Rui Meng and Tomas Pfister | [Science One Framework](https://research.google/blog/science-one-framework-a-verifiable-autonomous-research-framework-via-chain-of-evidence/), July 30, 2026 | Evidence-chain and independent-rerun ideas; explicitly experimental, not production tooling. No benchmark numbers adopted as achieved capabilities. |
| Google Research, Yubin Kim | [Wearable biomarker discovery framework](https://research.google/blog/an-ai-tool-for-prioritizing-candidate-biomarkers-from-wearable-sensor-data/), August 21, 2026 | Deterministic analysis, leakage controls, review and restrained interpretation; research report, not validated clinical product evidence. |
| FutureHouse, Sam Rodriques and listed research authors | [Robin](https://www.futurehouse.org/research/demonstrating-end-to-end-scientific-discovery-with-robin-a-multi-agent-system), updated May 19, 2026; original May 20, 2025 | Human wet-lab execution and computational orchestration boundary. Public repository linked; not installed or audited here. |
| Elicit | [Introducing Research Agent](https://elicit.com/blog/introducing-elicit-research-agent), August 4, 2026 | Documented commercial competitive scope; provider benchmark/customer statements remain claims. |
| Seqera, Evan Floden | [Co-Scientist launch](https://seqera.io/blog/co-scientist-launch/), April 30, 2026; [current CLI docs](https://docs.seqera.io/platform-cloud/co-scientist/) | Close bioinformatics competitor. Distinguish documented current CLI functions from launch roadmap language. No authenticated product test. |
| Code Ocean | [Compute Capsule](https://docs.codeocean.com/osl-guide/getting-started/what-is-a-compute-capsule), undated current documentation | Code/data/environment packaging. No inference of paper-level correctness from packaging. |
| Galaxy Project | [FAIR principles](https://galaxyproject.org/fair/), current documentation | Existing workflow/history/provenance and sharing capabilities; deployment not tested. |
| Swiss Data Science Center | [How Renku works](https://docs.renkulab.io/en/latest/docs/users/knowledge-base/about/), current Renku docs | Code/data/compute, sessions and Apache-2.0; avoid relying on superseded version-1 behavior. |
| iSEE authors / Bioconductor | [Interface vignette](https://bioconductor.posit.co/packages/release/bioc/vignettes/iSEE/inst/doc/basic.html), current release | Existing interactive scientific exploration. Functionality documented, not executed here. |
| JupyterHub contributors | [BinderHub source](https://github.com/jupyterhub/binderhub), current repository | Environment/session alternative. No claim of durable research record or hostile-code safety. |

## Demonstrator papers and actual artifacts

| Source | Publication/version | Checked artifacts |
|---|---|---|
| Law CW et al., [RNA-seq analysis is easy as 1-2-3](https://pmc.ncbi.nlm.nih.gov/articles/PMC4937821/) | Version 3, December 28, 2018, [DOI](https://doi.org/10.12688/f1000research.9005.3); original June 17, 2016 | [Official full-text XML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC4937821/fullTextXML), selected figure/caption/methods and session information. Figure not rendered here. |
| Bioconductor, [RNAseq123](https://bioconductor.org/packages/release/workflows/html/RNAseq123.html) | Release page 3.23; package 1.36.0, packaged June 2, 2026; DESCRIPTION source commit prefix `09a5145` | [Versioned package archive](https://bioconductor.org/packages/3.23/workflows/src/contrib/RNAseq123_1.36.0.tar.gz), DESCRIPTION and [R vignette](https://bioconductor.org/packages/3.23/workflows/vignettes/RNAseq123/inst/doc/limmaWorkflow.R). Artistic-2.0 verified. Current package is not a historical execution receipt. |
| NCBI GEO, [GSE63310](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE63310) | Public March 15, 2015; series last update January 11, 2022 | [Full series text](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE63310&targ=self&form=text&view=full), [count archive](https://www.ncbi.nlm.nih.gov/geo/download/?acc=GSE63310&format=file); nine selected files parsed with bounded Python checks. |
| Bioconductor edgeR source | `RELEASE_3_8`, function comment created November 13, 2017 | [filterByExpr.R](https://raw.githubusercontent.com/bioc/edgeR/RELEASE_3_8/R/filterByExpr.R); 1,550 bytes, hash in receipt. Used only for a small independent filtering probe; branch is not itself an immutable full runtime pin. |
| Chen Y, Lun ATL, Smyth GK, [From reads to genes to pathways](https://pmc.ncbi.nlm.nih.gov/articles/PMC4934518/) | Version 2, August 2, 2016, [DOI](https://doi.org/10.12688/f1000research.8987.2) | [XML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC4934518/fullTextXML), [R script](https://bioconductor.org/packages/3.23/workflows/vignettes/RnaSeqGeneEdgeRQL/inst/doc/edgeRQL.R), [package page](https://bioconductor.org/packages/release/workflows/html/RnaSeqGeneEdgeRQL.html), [count file](https://www.ncbi.nlm.nih.gov/geo/download/?acc=GSE60450&format=file&file=GSE60450%5FLactation%2DGenewiseCounts%2Etxt%2Egz). Page lists package 1.36.0 and Artistic-2.0; exact archive license must still be sealed when used. |
| Love MI, Anders S, Kim V, Huber W, [RNA-Seq workflow](https://pmc.ncbi.nlm.nih.gov/articles/PMC4670015/) | XML inspected is version 1, October 14, 2015, [DOI](https://doi.org/10.12688/f1000research.7035.1) | [XML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC4670015/fullTextXML), [rnaseqGene source at inspected commit](https://github.com/thelovelab/rnaseqGene/tree/0d7e27dde3ca9875cf94770ed9de35e346dd3676); current source differs from original article. |
| Bioconductor, [airway](https://bioconductor.org/packages/release/data/experiment/html/airway.html) | Release page 3.23, package 1.32.0, LGPL | Metadata accessed; full current and historical archive probes stopped at byte caps. No package installation or matrix deserialization. |
| Himes BE et al., [CRISPLD2 airway study](https://pmc.ncbi.nlm.nih.gov/articles/PMC4057123/) | June 13, 2014, [DOI](https://doi.org/10.1371/journal.pone.0099625) | [XML](https://www.ebi.ac.uk/europepmc/webservices/rest/PMC4057123/fullTextXML), original computational/wet-lab figure scope. Excluded as an immediate whole-study reproduction. |

Exact primary-case observations, hashes and measurement limits are in [feasibility.json](../evidence/feasibility.json). Downloaded research materials were inspected in temporary storage and are not bundled into this planning folder. Reacquisition is specified by URLs and hashes; source HTTP responses alone were not treated as successful scientific runs.

## Infrastructure, provenance and access

| Maintainer | Reference | Decision informed |
|---|---|---|
| NIH/NLM | [PMC Open Access Subset](https://pmc.ncbi.nlm.nih.gov/tools/openftlist/), modified August 24, 2026 | Article-specific reuse terms and supported retrieval routes; PMC inclusion alone is insufficient for unrestricted reuse. |
| NCBI GEO | [Disclaimer](https://www.ncbi.nlm.nih.gov/geo/info/disclaimer.html), modified July 8, 2026 | Public data access with explicit third-party-rights caveat. |
| NIH/NLM | [ClinicalTrials.gov API](https://clinicaltrials.gov/data-api/about-api), [version endpoint](https://clinicaltrials.gov/api/v2/version) | Direct endpoint returned API 2.0.5, `dataTimestamp=2026-09-11T09:00:04`. No trial-history or entity-linking functionality tested. |
| Seqera / Nextflow | [Cache and resume](https://docs.seqera.io/nextflow/cache-and-resume), current docs | Existing scientific task cache; not equivalent to immutable reviewed results. |
| Snakemake | [Distribution and reproducibility](https://snakemake.readthedocs.io/en/stable/snakefiles/deployment.html), page identified 9.27.0 | Workflow/environment alternative; not installed or benchmarked. |
| Temporal | [Activity execution source documentation](https://github.com/temporalio/documentation/blob/main/docs/encyclopedia/activities/activity-execution.mdx), current | Retry/heartbeat/cancellation considerations; actual workload stop must still be verified. |
| LangChain | [LangGraph durable execution](https://docs.langchain.com/oss/python/langgraph/durable-execution), current | Model workflow alternative; application side effects still need deterministic/idempotent design. |
| PostgreSQL | [SELECT and locking](https://www.postgresql.org/docs/current/sql-select.html), documentation 18 | `SKIP LOCKED` work claiming; application fencing and invariants remain implementation responsibilities. |
| Docling Project | [Document model](https://docling-project.github.io/docling/concepts/docling_document/), [MIT license](https://github.com/docling-project/docling/blob/main/LICENSE), current | Retain typed layout/provenance; model-weight licenses separately verified before adoption. |
| GROBID | [Coordinates](https://grobid.readthedocs.io/en/latest/Coordinates-in-PDF/), [Apache-2.0 license](https://github.com/grobidOrg/grobid/blob/master/LICENSE), current | Alternative scientific PDF parser and coordinate alignment reference. |
| W3C | [PROV Overview](https://www.w3.org/TR/prov-overview/), April 30, 2013 | Entity/activity/actor vocabulary; no graph database required. |
| ResearchObject | [Provenance Run Crate](https://www.researchobject.org/workflow-run-crate/profiles/provenance_run_crate/), profile 0.5 | Export interoperability; conformance not achieved yet. |
| Docker | [Engine security](https://docs.docker.com/engine/security/), current | Privileged daemon and container trust boundary; no certification of the local engine. |
| gVisor | [Architecture and purpose](https://gvisor.dev/docs/), current | Stronger Linux sandbox option, subject to workload compatibility tests. |
| DVC maintainers | [Pipeline documentation source](https://github.com/treeverse/dvc.org/blob/main/content/docs/start/data-pipelines/data-pipelines.md), current | Versioning/build graph alternative. |
| MLflow | [Experiment tracking](https://mlflow.org/docs/latest/ml/tracking), current | Existing run/parameter/artifact management; optional export, no duplicate source of truth initially. |

## Local evidence and unresolved questions

[Repository inspection receipts](../evidence/repository-inspection.json) record HEADs and selected file hashes. [REUSE](REUSE.md) links the exact inspected source files and distinguishes static findings from tested behavior. The Mac tool/version observations and installed Colima help are recorded in [operations](OPERATIONS-LEARNING.md); no paid services or existing repository runtimes were exercised.

Unresolved evidence: historical R build and full numerical/plot reproduction; PDF-to-JATS target alignment; exact archived dependency and data-redistribution notices; real user adoption; agent quality on held-out papers; hostile-code safety and recovery behavior on the intended runtime. These become explicit implementation gates rather than claims in the product description.
