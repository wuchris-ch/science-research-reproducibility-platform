# Scientific adapters

Law et al. 2018 v3 (DOI 10.12688/f1000research.9005.3) and Chen et al. 2016 v2 (DOI 10.12688/f1000research.8987.2) are attributed under their CC BY licenses. Public count data retain GEO attribution and access terms. Package source licenses remain in their source distributions.

The executable adapter implements named operations from the papers. It adds strict input validation, parameter input, machine-readable observables and headless plotting. It removes interactive Glimma output, online retrieval and symbol annotation where symbols are presentation labels only (Law). Gene IDs and counts remain intact. The original current tutorial digest is in `evidence/feasibility.json`; the versioned paper is the authority when current tutorial code differs.

Law density uses raw library sizes, prior count 2, the edgeR 3.24.0 expression filter for three equal groups and recalculated library sizes after filtering. The controlled CPM > 1 alternative is explicitly a variation. Density grids come from R's `density`; a rendered pixel match is not asserted. Font, operating system and raster rendering differ from the paper.

Law differential expression uses TMM, voom, `~0+group+lane`, limma empirical Bayes and one selected contrast. It exports all tested genes and Benjamini-Hochberg adjusted P values for that contrast. This is the paper's eBayes analysis, not its later TREAT test with a twofold threshold. Symbols are omitted to preserve stable Entrez identifiers without silently substituting an annotation release.

Chen MDS uses the original org.Mm.eg.db 3.3.0 symbol availability to drop unannotated genes, CPM > 0.5 in at least two samples, recalculated library sizes, TMM and pairwise leading log-fold-change MDS. Its historical paper used R 3.3.1, edgeR 3.14.0 and limma 3.28.6 on Windows. The shared reference runtime uses R 3.5.1, edgeR 3.24.0 and limma 3.38.3 on Linux. This is an explicitly adapted environment, not an exact historical reconstruction. MDS coordinates may change sign without changing distances.

Only curated recipes execute. User-supplied text and extraction suggestions cannot become shell commands or R code. Reviewed variations change typed parameters. Arbitrary analysis-code patches remain gated on a separately validated stronger execution service; a local Docker daemon is not a sufficient boundary for hostile code.
