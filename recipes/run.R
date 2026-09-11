# Adapted scientific operations from Law et al. (2018), CC BY 4.0,
# DOI 10.12688/f1000research.9005.3 and Chen et al. (2016), CC BY 4.0,
# DOI 10.12688/f1000research.8987.2. See ADAPTATIONS.md for each change.
suppressPackageStartupMessages({library(edgeR); library(limma); library(jsonlite); library(RColorBrewer)})
p <- fromJSON(Sys.getenv('PLAN_JSON'))
set.seed(p$parameters$seed)
q <- p$parameters
out <- '/work/output'
dir.create(out, recursive=TRUE, showWarnings=FALSE)
writeLines(capture.output(sessionInfo()), file.path(out, 'session.txt'))
if (p$dataset_id == 'law2018') {
    map <- read.csv('/app/law-samples.csv', stringsAsFactors=FALSE)
    tables <- lapply(map$file, function(f) read.delim(file.path('/data/law2018', f), stringsAsFactors=FALSE))
    stopifnot(all(sapply(tables, function(t) identical(t$EntrezID, tables[[1]]$EntrezID))))
    counts <- do.call(cbind, lapply(tables, function(t) t$Count))
    rownames(counts) <- tables[[1]]$EntrezID
    colnames(counts) <- map$sample
    group <- factor(map$group)
} else {
    t <- read.delim('/data/chen2016/counts.tsv', row.names=1)
    counts <- as.matrix(t[,-1])
    colnames(counts) <- substring(colnames(counts),1,7)
    group <- factor(paste(rep(c('B','L'),each=6), rep(rep(c('virgin','pregnant','lactating'),each=2),2),sep='.'))
}
stopifnot(all(is.finite(counts)), all(counts >= 0), all(counts == floor(counts)), !anyDuplicated(rownames(counts)))
x <- DGEList(counts, group=group)
original.libs <- colSums(counts)
raw <- cpm(x, log=TRUE)
M <- median(original.libs)*1e-6
L <- mean(original.libs)*1e-6
cutoff <- log2(q$min_count/M + 2/L)
if (p$dataset_id == 'chen2016') {
    symbols <- read.delim('/data/chen2016/symbols.tsv', stringsAsFactors=FALSE)
    x <- x[rownames(x) %in% symbols$gene_id, ]
    annotated.genes <- nrow(x)
    # Historical article uses 0.5 CPM in at least two samples.
    keep <- rowSums(cpm(x) > if (q$filter_policy == 'published') 0.5 else 1) >= 2
} else if (q$filter_policy == 'cpm1') {
    keep <- rowSums(cpm(x) > 1) >= q$min_samples
} else {
    # Equal-size design, declared minimum group size; edgeR 3.24.0 rule.
    keep <- rowSums(cpm(x) >= q$min_count/M) >= q$min_samples & rowSums(x$counts) >= q$min_total_count
}
all.ids <- rownames(counts)
retained <- rownames(x)[keep]
x <- x[keep,,keep.lib.sizes=FALSE]
stopifnot(nrow(x) > 500)
filtered <- cpm(x, log=TRUE)
write.table(data.frame(gene_id=all.ids, retained=all.ids %in% retained),file.path(out,'genes.tsv'),sep='\t',quote=FALSE,row.names=FALSE)
write.table(data.frame(sample=colnames(counts),group=as.character(group),library_size=original.libs,filtered_library_size=x$samples$lib.size),file.path(out,'samples.tsv'),sep='\t',quote=FALSE,row.names=FALSE)
metrics <- list(schema_version=1, dataset_id=p$dataset_id, recipe=p$recipe, input_genes=nrow(counts), samples=ncol(counts), all_zero_genes=sum(rowSums(counts)==0), retained_genes=nrow(x), library_sizes=as.list(original.libs), parameters=q)
if (p$recipe == 'density') {
    colors <- brewer.pal(ncol(counts),'Paired')
    grids <- data.frame()
    png(file.path(out,'figure.png'),width=1440,height=720,res=160)
    par(mfrow=c(1,2),mar=c(4.2,4.2,3,1))
    for (stage in c('raw','filtered')) {
        mat <- if(stage == 'raw') raw else filtered
        for (i in seq_len(ncol(mat))) {
            d <- density(mat[,i])
            if(i == 1) {
                plot(d,col=colors[i],lwd=2,ylim=c(0,0.26),las=1,main=if(stage=='raw') 'A. Raw data' else 'B. Filtered data',xlab='Log-CPM')
                abline(v=cutoff,lty=3)
            } else lines(d$x,d$y,col=colors[i],lwd=2)
            grids <- rbind(grids,data.frame(stage=stage,sample=colnames(mat)[i],x=d$x,y=d$y))
        }
        legend('topright',colnames(mat),text.col=colors,bty='n',cex=0.65)
    }
    dev.off()
    write.table(grids,file.path(out,'density.tsv'),sep='\t',quote=FALSE,row.names=FALSE)
    metrics$cpm_cutoff <- q$min_count/M
    metrics$log_cpm_cutoff <- cutoff
    metrics$raw_summary <- unclass(apply(raw,2,summary))
    metrics$filtered_summary <- unclass(apply(filtered,2,summary))
} else if(p$recipe == 'differential') {
    x <- calcNormFactors(x,method='TMM')
    lane <- factor(map$lane)
    design <- model.matrix(~0+group+lane)
    colnames(design) <- gsub('group','',colnames(design))
    contrasts <- makeContrasts(BasalvsLP=Basal-LP,BasalvsML=Basal-ML,LPvsML=LP-ML,levels=design)
    v <- voom(x,design,plot=FALSE)
    fit <- eBayes(contrasts.fit(lmFit(v,design),contrasts=contrasts))
    tab <- topTable(fit,coef=q$contrast,n=Inf,sort.by='P')
    tab <- data.frame(gene_id=rownames(tab),tab,stringsAsFactors=FALSE)
    write.table(tab,file.path(out,'differential.tsv'),sep='\t',quote=FALSE,row.names=FALSE)
    write.table(design,file.path(out,'design.tsv'),sep='\t',quote=FALSE,col.names=NA)
    png(file.path(out,'figure.png'),width=1200,height=800,res=160)
    plot(tab$logFC,-log10(pmax(tab$adj.P.Val,.Machine$double.xmin)),pch=16,cex=.35,col=ifelse(tab$adj.P.Val < q$fdr,'#20786b','#bfc6ca'),xlab=paste('log2 fold change:',q$contrast),ylab='-log10 adjusted P',main='Differential expression')
    abline(h=-log10(q$fdr),lty=3)
    dev.off()
    metrics$design <- '~0+group+lane'
    metrics$normalization <- 'TMM'
    metrics$multiple_testing <- 'Benjamini-Hochberg across the full tested universe, per contrast'
    metrics$significant_genes <- sum(tab$adj.P.Val < q$fdr)
    metrics$up <- sum(tab$adj.P.Val < q$fdr & tab$logFC > 0)
    metrics$down <- sum(tab$adj.P.Val < q$fdr & tab$logFC < 0)
} else {
    x <- calcNormFactors(x,method='TMM')
    colors <- rep(c('darkgreen','red','blue'),2)
    shapes <- c(0,1,2,15,16,17)
    png(file.path(out,'figure.png'),width=1100,height=900,res=160)
    m <- plotMDS(x,col=colors[group],pch=shapes[group],main='Leading log-fold-change distances')
    legend('topleft',legend=levels(group),pch=shapes,col=colors,ncol=2,cex=.7)
    dev.off()
    write.table(data.frame(sample=colnames(x),group=as.character(group),x=m$x,y=m$y),file.path(out,'mds.tsv'),sep='\t',quote=FALSE,row.names=FALSE)
    metrics$annotated_genes <- annotated.genes
    metrics$normalization_factors <- as.list(x$samples$norm.factors)
}
write_json(metrics,file.path(out,'metrics.json'),auto_unbox=TRUE,digits=16,pretty=TRUE,na='null')
cat('Completed',p$recipe,'with',nrow(x),'retained genes\n')
