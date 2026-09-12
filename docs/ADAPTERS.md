# Study adapters

Scientific capabilities are declared in `src/workbench/manifests/adapter-*.json` and validated by `Adapter` at registration. A plan stores the complete adapter and its SHA-256. A locked plan retains that version even when a later application adds capabilities.

A manifest declares a unique identity, semantic version, recipe, registered runtime, input contract, bounded typed parameters, optional sensitivity choices, required and numerical outputs, methods, adaptations, and primary references. Unknown fields, invalid defaults, unsupported parameter values and unsafe output names are rejected. The manifest cannot contain executable commands, downloaded code, image names, or arbitrary file paths. Changing the trusted R implementation requires a repository change, runtime rebuild and new adapter version.

The curated source register is `datasets.json`. It associates a source version and content hash with supported adapters and any dataset-specific defaults or constraints. Imported studies use the `paired-counts-v1` contract and the registered paired DESeq2 adapter. Adding another compatible dataset does not require a new dataset branch in the statistical implementation.

The paired contract accepts `counts.tsv` with `gene_id` followed by sample IDs and `samples.tsv` with `sample`, `donor`, and `condition`. Counts are unnormalized nonnegative integers; sample IDs must form an exact bijection; each donor must have one control and one treated sample. Review the experimental units before assigning donor IDs. Accepted uploads are immutable, workspace-scoped artifacts. All variants share those exact bytes.

Publication references are comparator inputs, held outside the scientific container. Runtime consistency checks and independently reported values are displayed separately. An executed adapter must emit the declared complete numerical outputs, including untested genes and exclusion reasons for differential expression.
