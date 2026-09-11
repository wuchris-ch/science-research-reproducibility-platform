FROM --platform=linux/amd64 rocker/r-ver:3.5.1@sha256:af1a00a587e977748a85a129fb1eb35bee469b2f81b49c9c338a58a9143f1f48
COPY packages /packages
RUN R CMD INSTALL /packages/Rcpp_1.0.0.tar.gz && R CMD INSTALL /packages/locfit_1.5-9.1.tar.gz && R CMD INSTALL /packages/limma_3.38.3.tar.gz && R CMD INSTALL /packages/edgeR_3.24.0.tar.gz && R CMD INSTALL /packages/RColorBrewer_1.1-2.tar.gz && R CMD INSTALL /packages/jsonlite_1.6.tar.gz && rm -rf /packages
COPY data /data
COPY run.R law-samples.csv entrypoint.sh /app/
RUN chmod 755 /app/entrypoint.sh && chmod -R a+rX /app /data
ENV HOME=/work TMPDIR=/work LC_ALL=C TZ=UTC OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
USER 1000:1000
WORKDIR /work
ENTRYPOINT ["/app/entrypoint.sh"]
