# Demo paper and feasibility

> Design record from the planning phase. See [implemented behavior and evidence](IMPLEMENTED.md) and the [current operating guide](RUNBOOK.md) for delivered capabilities and remaining gates.

[Start](../README.md) · [Backlog](IMPLEMENTATION.md) · [Probe receipt](../evidence/feasibility.json) · [Sources](SOURCES.md)

## Primary case

**Law CW et al., “RNA-seq analysis is easy as 1-2-3 with limma, Glimma and edgeR,” version 3, December 28, 2018, DOI 10.12688/f1000research.9005.3.** The first version appeared June 17, 2016. Pin version 3, not a mutable landing page. Target **Figure 1A/B: sample log-CPM density before and after low-expression filtering**. The workflow uses nine mouse mammary cell-population samples from GSE63310. The first slice begins at gene counts, not sequencing reads. [Article](https://pmc.ncbi.nlm.nih.gov/articles/PMC4937821/), [versioned publisher page](https://f1000research.com/articles/5-1408/v3).

This is deliberately a published methods workflow. It offers a tractable first end-to-end case and a clear explanation of the computation. It is not evidence that arbitrary biomedical papers can be reproduced. After the slice works, extend the same workspace to a differential-expression comparison using the paper's declared design and contrast, then add a genuinely independent study.

## What was actually checked

Anonymous requests retrieved the article's JATS XML through Europe PMC, the current RNAseq123 source archive, its executable R vignette, the GEO series record and count archive. The PMC HTML sometimes returned a browser challenge and the Love publisher page returned HTTP 403, so source XML was used as an official machine-readable route. No access bypass, credentials, R package installation or author-code execution was used.

| Artifact | Observed evidence | Limit |
|---|---|---|
| Article | JATS XML identifies version 3 and its figure/method sections | PDF page coordinates and rendering have not yet been checked |
| GEO archive | 1,996,800 bytes; 11 gzip members, of which the recipe explicitly selects nine | Do not silently include the two excluded samples |
| Selected data | Each file has 27,179 unique matching gene IDs; nonnegative integer counts; identical row order | This validates structure, not original sequencing or sample labels |
| Count checks | Nine library totals match the article's displayed input table; 5,153 rows have zero counts in all nine samples | No biological-quality conclusion follows |
| Filtering probe | A small Python translation of the inspected historical filter rule retained 16,624 genes; alternative CPM > 1 in at least three samples retained 14,165 | No R/edgeR run, density plot or full reproduction was performed |
| Workflow code | RNAseq123 1.36.0 archive, 7,259,084 bytes, Artistic-2.0; R script contains data selection, filtering and Figure 1 plotting | Current package is not automatically the version-3 historical environment |

[GEO series](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE63310), [count archive](https://www.ncbi.nlm.nih.gov/geo/download/?acc=GSE63310&format=file), [package](https://bioconductor.org/packages/release/workflows/html/RNAseq123.html), [R script](https://bioconductor.org/packages/3.23/workflows/vignettes/RNAseq123/inst/doc/limmaWorkflow.R), [historical filter implementation](https://raw.githubusercontent.com/bioc/edgeR/RELEASE_3_8/R/filterByExpr.R).

The [receipt](../evidence/feasibility.json) contains all nine filenames, compressed and decompressed hashes, sizes, library totals, source URLs and probe limits. The archive SHA-256 is `8cb208fdef9254dc78162bdbeb958e179eba7f015716d74d2d4b34e12f36fbe8`. Preserve both byte hashes and parsed-matrix identity because archives may be repacked without changing numerical content.

## Exact recipe boundary

The planned adapter selects the nine filenames in the receipt in their stated order. Groups are `LP, ML, Basal, Basal, ML, LP, Basal, ML, LP`; lanes are `L004` for the first three, `L006` for the next four and `L008` for the last two. Store sample identity explicitly, not just vector position. The two omitted GEO samples belong to other experimental populations; exclusions are part of the published recipe, not a later choice made to improve results.

Execute the relevant source chunks through count import, sample mapping, log-CPM, filtering and `filterplot1`. For this figure, the gene annotation package does not supply the numerical inputs to filtering or density. Removing annotation loading from a minimal adapter is still a documented code adaptation. Save the upstream script and a separate patch explaining omitted unrelated chunks. Do not label the result an unchanged whole-script rerun.

Historical numerical environment target: R 3.5.1, edgeR 3.24.0, limma 3.38.3, RColorBrewer 1.1-2, as reported in the version-3 session information. The original reported platform was macOS x86_64. An archived Linux image with equivalent package versions remains a reconstructed environment, not that exact original machine. Inspect archived packages, pin checksums, and record all transitive versions before choosing a digest. No historical image or build has been verified yet.

Use modern maintained R as a second profile only after the reference profile is evaluated. Label it **modernized reanalysis** with explicit differences. Do not install the entire latest workflow dependency tree to draw one figure. Freeze language, package, OS, BLAS, locale, architecture and plotting settings. Modern and historical profiles must have distinct cache keys.

## Comparison and the controlled variation

For the first run, check exact sample/gene identities, counts, library totals, retained count and retained-ID set where a trusted reference exists. Export the density grid and values, cutoff, raw/filtered log-CPM summaries, PNG, session information and logs. The paper supplies a plotted reference, not a downloadable numerical density oracle. A newly executed reference cannot be presented as independently supplied paper data.

Compare to the paper in layers: exact published scalar checks; human review of the correct figure panel and labels; bounded image/digitization comparison only where justified; fresh rerun consistency against a sealed reference. Do not declare the whole figure numerically reproduced from a visually similar PNG. Mark untestable parts `reference_unavailable`.

The article's version history documents a relaxed filtering strategy in version 3. Use that as a real source-version discrepancy to investigate. Prespecify one variation, CPM > 1 in at least three samples, with all other choices fixed. The probe produced 2,459 fewer retained genes under that rule. This is a controlled sensitivity result; do not claim the old rule constitutes a full version-2 rerun until the version-2 code and environment are separately checked. Do not tune the filter until the picture “looks right.”

## License and access ledger

| Object | Verified terms/access | Planned handling |
|---|---|---|
| Law article | Article copyright statement permits reuse under Creative Commons Attribution | Retain citation and exact version; verify any third-party figure notices before bundling PDF/figures |
| RNAseq123 source | DESCRIPTION: Artistic-2.0 | Keep upstream source identity, notices and patch history; respect dependency licenses |
| edgeR / limma | Bioconductor package licenses are separate from the article and workflow | Inventory exact archived versions and include source/license obligations with any distributed image |
| GSE63310 | Anonymous public download verified; GEO imposes no additional restrictions but warns submitters may retain rights | No separate dataset-specific SPDX license was found in the series record. Use attributed source retrieval for v1; do not relabel counts as CC0 or MIT |
| Application | Not yet licensed | Choose a license for new code independently of third-party materials |

[GEO disclaimer, updated July 8, 2026](https://www.ncbi.nlm.nih.gov/geo/info/disclaimer.html). Public access and a package license are not universal permission for every upstream item. The initial local demo is feasible under the documented access/reuse terms; a publicly redistributed dataset/image bundle requires a completed component notice inventory. Export can contain source URLs and hashes instead of redistributing uncertain materials.

## Fallback shortlist

| Rank | Actual open paper and target | Code/data checked | Why it is a fallback |
|---|---|---|---|
| 2 | Chen, Lun and Smyth, **From reads to genes to pathways**, version 2, August 2, 2016, DOI 10.12688/f1000research.8987.2; Figure 1 MDS from processed counts | Official JATS XML retrieved; current RnaSeqGeneEdgeRQL R script inspected; GSE60450 count file downloaded: 513,592 compressed bytes, 27,179 rows and 12 sample columns | Same broad workflow family, different experiment. Annotation version, historical filtering and MDS defaults need pinning; current script is not the article's historical script. [Paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC4934518/), [package](https://bioconductor.org/packages/release/workflows/html/RnaSeqGeneEdgeRQL.html), [code](https://bioconductor.org/packages/3.23/workflows/vignettes/RnaSeqGeneEdgeRQL/inst/doc/edgeRQL.R) |
| 3 | Love, Anders, Kim and Huber, **RNA-Seq workflow: gene-level exploratory analysis and differential expression**, version 1, October 14, 2015, DOI 10.12688/f1000research.7035.1; Figure 6 PCA | Official XML returned v1, not v2. Current rnaseqGene source inspected at `0d7e27dde3ca9875cf94770ed9de35e346dd3676`; Artistic-2.0. Airway package lists LGPL and four paired human cell lines | Human biomedical example, but rlog/DESeq2 historical compatibility is harder. Current and historical airway archive probes exceeded 12 MB and 6 MB caps respectively and were stopped; no R object was loaded. [Paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC4670015/), [source](https://github.com/thelovelab/rnaseqGene/tree/0d7e27dde3ca9875cf94770ed9de35e346dd3676), [airway](https://bioconductor.org/packages/release/data/experiment/html/airway.html) |

Chen article XML declares CC BY 4.0; processed data uses GEO terms. The current RnaSeqGeneEdgeRQL 1.36.0 page lists Artistic-2.0. Before using its code, seal the exact selected archive's DESCRIPTION/license rather than inheriting another package's terms. Love article XML declares CC BY 4.0; the airway package declares LGPL, without resolving every underlying-data right. These are usable candidates with explicit remaining checks, not certified reproductions.

Himes et al.'s 2014 CRISPLD2 airway study was also inspected. Its Figure 1 uses the original differential-expression pipeline and other figures depend on wet-lab measurements. The DESeq2 teaching workflow is not a reproduction of that original pipeline. Do not substitute its counts and claim to reproduce the Himes study. [Original study](https://pmc.ncbi.nlm.nih.gov/articles/PMC4057123/).

## Compute envelope and decision gates

The primary matrix contains 244,611 counts, about 1.9 MiB as float64 before object overhead. Parsing was small and CPU-only. Proposed initial limits are 2 vCPU, 4 GiB RAM, 2 GiB writable scratch and 10 minutes per numerical attempt. These are engineering budgets, not measured R performance. Environment building is separate, with a 30-minute/10-GB cap. No GPU is required.

Gate P0.1 on a real R run and a source-to-output audit. If the historical environment cannot be built inside the bounded effort, record the failure and use a modernized profile with explicit comparison limits. If Figure 1 cannot be credibly compared, keep the narrower exact input/filter result as partial work, then evaluate the Chen fallback. Never silently relax the target or tolerance and call the primary reproduction complete.
