# Adapted from Love et al. 2015 v1, CC BY 4.0, DOI 10.12688/f1000research.7035.1.
# Inputs conform to paired-counts-v1. No expected publication values enter this process.
suppressPackageStartupMessages({library(DESeq2); library(jsonlite)})
p <- fromJSON(Sys.getenv('PLAN_JSON'))
q <- p$parameters
set.seed(q$seed)
out <- '/work/output'
dir.create(out, recursive=TRUE, showWarnings=FALSE)
writeLines(capture.output(sessionInfo()), file.path(out, 'session.txt'))
root <- file.path(Sys.getenv('INPUT_ROOT', '/data'), p$dataset_id)
counts <- as.matrix(read.delim(file.path(root, 'counts.tsv'), row.names=1, check.names=FALSE))
samples <- read.delim(file.path(root, 'samples.tsv'), stringsAsFactors=FALSE)
stopifnot(!anyDuplicated(rownames(counts)), !anyDuplicated(colnames(counts)),
          !anyDuplicated(samples$sample), setequal(samples$sample, colnames(counts)),
          all(is.finite(counts)), all(counts >= 0), all(counts <= .Machine$integer.max),
          all(counts == floor(counts)))
samples <- samples[match(colnames(counts), samples$sample), ]
rownames(samples) <- samples$sample
samples$donor <- factor(samples$donor)
samples$condition <- factor(samples$condition, levels=c('control','treated'))
stopifnot(!anyNA(samples$condition), all(table(samples$donor, samples$condition) == 1))
design <- model.matrix(~ donor + condition, samples)
stopifnot(qr(design)$rank == ncol(design), nrow(design) > ncol(design))
storage.mode(counts) <- 'integer'
keep <- rowSums(counts) >= q$min_total_count
stopifnot(sum(keep) >= 100)
dds <- DESeqDataSetFromMatrix(countData=counts[keep, ], colData=samples, design=~ donor + condition)
dds <- estimateSizeFactors(dds, type=q$size_factor)
dds <- DESeq(dds, fitType='parametric', betaPrior=q$beta_prior, parallel=FALSE, quiet=TRUE)
res <- results(dds, contrast=c('condition','treated','control'), alpha=q$fdr,
               independentFiltering=q$independent_filtering, pAdjustMethod='BH')
tab <- as.data.frame(res)
tab$status <- ifelse(is.na(tab$pvalue), 'cook_outlier',
                     ifelse(is.na(tab$padj), 'independently_filtered', 'tested'))
effects <- data.frame(gene_id=rownames(counts), baseMean=NA_real_, log2FoldChange=NA_real_,
                      lfcSE=NA_real_, stat=NA_real_, pvalue=NA_real_, padj=NA_real_,
                      status='excluded_low_total', stringsAsFactors=FALSE)
effects[keep, names(tab)] <- tab
write.table(effects, file.path(out,'effects.tsv'), sep='\t', quote=FALSE, row.names=FALSE, na='NA')
write.table(data.frame(gene_id=rownames(counts),retained=keep), file.path(out,'genes.tsv'),sep='\t',quote=FALSE,row.names=FALSE)
libs <- colSums(counts)
sf <- sizeFactors(dds)
write.table(data.frame(sample=samples$sample,donor=samples$donor,group=samples$condition,
                       library_size=libs,filtered_library_size=colSums(counts[keep,]),size_factor=sf),
             file.path(out,'samples.tsv'),sep='\t',quote=FALSE,row.names=FALSE)
normalized <- sweep(counts, 2, sf, '/')
write.table(data.frame(gene_id=rownames(counts), normalized, check.names=FALSE),
             file.path(out,'normalized-counts.tsv'),sep='\t',quote=FALSE,row.names=FALSE)
write.table(design,file.path(out,'design.tsv'),sep='\t',quote=FALSE,col.names=NA)
tested <- !is.na(tab$padj)
significant <- !is.na(tab$padj) & tab$padj < q$fdr
metrics <- list(schema_version=1,dataset_id=p$dataset_id,recipe=p$recipe,input_genes=nrow(counts),
                samples=ncol(counts),all_zero_genes=sum(rowSums(counts)==0),retained_genes=sum(keep),
                library_sizes=as.list(libs),parameters=q,design='~ donor + condition',
                contrast='treated versus control',normalization=q$size_factor,
                multiple_testing='Benjamini-Hochberg within the independently filtered tested universe',
                pvalue_genes=sum(!is.na(tab$pvalue)),tested_genes=sum(tested),
                independent_filtered=sum(!is.na(tab$pvalue) & is.na(tab$padj)),
                cook_outliers=sum(is.na(tab$pvalue)),significant_genes=sum(significant),
                up=sum(significant & tab$log2FoldChange > 0,na.rm=TRUE),
                down=sum(significant & tab$log2FoldChange < 0,na.rm=TRUE),
                size_factors=as.list(sf),filter_threshold=if(q$independent_filtering) unname(metadata(res)$filterThreshold) else 0,
                dispersion_fit=attr(dispersionFunction(dds),'fitType'),
                fold_change_estimator=if(q$beta_prior) 'normal-prior MAP' else 'maximum likelihood')
png(file.path(out,'figure.png'),width=1280,height=860,res=160)
par(mar=c(4.5,4.5,3,1))
plot(pmax(tab$baseMean,0.1),tab$log2FoldChange,log='x',pch=16,cex=.4,
     col=ifelse(significant,'#20786b','#bfc6ca'),xlab='Mean normalized count',
     ylab='log2 fold change: treated / control',main='Donor-adjusted treatment response')
abline(h=0,lty=3,col='#55635f')
dev.off()
write_json(metrics,file.path(out,'metrics.json'),auto_unbox=TRUE,digits=16,pretty=TRUE,na='null')
cat('Completed donor-adjusted DESeq2 with',sum(keep),'retained genes\n')
