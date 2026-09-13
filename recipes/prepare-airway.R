# Decode the pinned airway 0.102.0 serialized slots without changing counts or identities.
# The historical GenomicRanges SummarizedExperiment predates the modern class layout.
untar('/data/airway.tar.gz', files='airway/data/airway.RData', exdir='/work')
load('/work/airway/data/airway.RData')
stopifnot(identical(class(airway)[1], 'SummarizedExperiment'))
container <- attr(attr(airway, 'assays'), '.xData')
counts <- attr(container$data, 'listData')[[1]]
ids <- attr(attr(attr(airway, 'rowData'), 'partitioning'), 'NAMES')
metadata <- as.data.frame(attr(attr(airway, 'colData'), 'listData'))
sample.ids <- attr(attr(airway, 'colData'), 'rownames')
stopifnot(nrow(counts) == length(ids), ncol(counts) == length(sample.ids),
          identical(as.character(metadata$Run), sample.ids), all(metadata$albut == 'untrt'))
colnames(counts) <- sample.ids
write.table(data.frame(gene_id=ids,counts,check.names=FALSE),'/work/counts.tsv',sep='\t',quote=FALSE,row.names=FALSE)
write.table(data.frame(sample=sample.ids,donor=metadata$cell,
                      condition=ifelse(metadata$dex=='trt','treated','control')),
            '/work/samples.tsv',sep='\t',quote=FALSE,row.names=FALSE)
write.table(metadata,'/work/supplement.tsv',sep='\t',quote=FALSE,row.names=FALSE)
