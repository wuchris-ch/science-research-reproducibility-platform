FROM node:22-bookworm-slim AS web
WORKDIR /build/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:0.9.16 AS uv
FROM python:3.12-slim-bookworm
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src/ src/
COPY fixtures/ fixtures/
COPY evidence/feasibility.json evidence/feasibility.json
COPY recipes/ recipes/
COPY environments/ environments/
COPY scripts/reproduce.py scripts/reproduce.py
COPY scripts/reproduce_study.py scripts/reproduce_study.py
COPY --from=web /build/web/dist web/dist
RUN uv sync --frozen --no-dev && groupadd -g 1000 workbench && useradd -u 1000 -g 1000 -M workbench && mkdir /data && chown 1000:1000 /data
ENV WORKBENCH_DATA_DIR=/data PATH=/app/.venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1
USER 1000:1000
EXPOSE 8317
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8317/api/health', timeout=3).read()"
ENTRYPOINT ["workbench"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8317"]
