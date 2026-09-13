FROM --platform=linux/amd64 debian:bookworm-20250203-slim@sha256:40b107342c492725bc7aacbe93a49945445191ae364184a6d24fedb28172f6f7
RUN rm /etc/apt/sources.list.d/debian.sources && printf 'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/20250203T000000Z bookworm main\n' > /etc/apt/sources.list && apt-get -o Acquire::Retries=3 update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends r-base-core=4.2.2.20221110-2 r-bioc-deseq2=1.38.3+dfsg-1 r-cran-jsonlite=1.8.4+dfsg-1 && rm -rf /var/lib/apt/lists/*
COPY data /data
COPY run.R entrypoint.sh locked-packages.json Dockerfile /app/
RUN dpkg-query -W -f='${Package}\t${Version}\n' > /app/system-packages.tsv && chmod 755 /app/entrypoint.sh && chmod -R a+rX /app /data
ENV HOME=/work TMPDIR=/work LC_ALL=C TZ=UTC OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
USER 1000:1000
WORKDIR /work
ENTRYPOINT ["/app/entrypoint.sh"]
