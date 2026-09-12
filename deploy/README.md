# Team deployment template

This configuration is for a private Linux host with Docker, PostgreSQL and an HTTPS reverse proxy. The API image was built and smoke-tested locally on September 11, 2026. The Compose file was configuration-checked; no public service, live OIDC tenant, or production database was deployed. The macOS loopback profile in the root README remains the verified complete local workflow.

## Boundaries

The API image contains Python, the compiled interface and source manifests. It contains no Docker CLI and receives no Docker socket. The worker runs as a separately supervised host process with access to the intended Docker engine. Both use the same PostgreSQL database and a private shared POSIX data directory. Containers executing scientific recipes receive no host mounts and cannot access API credentials, PostgreSQL or the shared artifact store.

The Compose template binds API port 8317 and database port 8318 only to loopback. Configure a trusted HTTPS reverse proxy in front of the API, preserving Host and forwarding requests to 8317. Set the exact public HTTPS origin. Limit request rate and aggregate storage at the infrastructure layer. The API refuses non-loopback serving without complete OIDC configuration.

## Prepare a host

Use a source checkout of the intended Git revision. Install Python 3.12+, uv, Node 22/npm and Docker CLI on the host. Prepare an absolute data directory owned by UID/GID 1000, shared with the API container; run the host worker under that identity. The default template expects `/data` inside the API. Host paths and secrets belong in an untracked `.env` with mode 600.

Configure these values:

```dotenv
POSTGRES_PASSWORD=replace-with-a-unique-random-hex-secret
POSTGRES_PORT=8318
WORKBENCH_DATA_DIR=/srv/research-workbench/data
WORKBENCH_DOCKER_CONTEXT=default
WORKBENCH_DATABASE_URL=postgresql+psycopg://workbench:the-same-secret@127.0.0.1:8318/workbench
WORKBENCH_ORIGINS=["https://research.example.org"]
WORKBENCH_OIDC_ISSUER=https://identity.example.org/tenant
WORKBENCH_OIDC_AUDIENCE=research-workbench
WORKBENCH_OIDC_JWKS_URL=https://identity.example.org/tenant/jwks
```

These are placeholders, not credentials or verified identity endpoints. Use the provider's issuer, audience and HTTPS JWKS values. The current UI accepts an already-issued RS256 access token; obtain it through your organization's approved identity flow. The token stays in the browser tab's session storage. No client secret is required by this API. Users create their own workspace and owners grant membership by exact provider subject.

Validate configuration without printing resolved secrets:

```sh
docker compose --env-file .env -f deploy/compose.yml config --quiet
```

Start the database, install/build the application and seal scientific inputs on the intended worker engine:

```sh
docker compose --env-file .env -f deploy/compose.yml up -d database
make setup
uv run workbench migrate
docker compose --env-file .env -f deploy/compose.yml build api
docker compose --env-file .env -f deploy/compose.yml up -d api
uv run workbench worker
```

`make setup` reads the host database URL from `.env`; the API's Compose environment uses the same database through the internal `database` hostname. Runtime registration is shared through the data directory. The worker should then be managed by the host's service supervisor. A Linux systemd template is included as `workbench-worker.service`; adapt its checkout path before installing it. The worker reads the protected `.env` in its working directory through the application configuration loader. Docker access gives this trusted worker broad host privileges and must not be granted to arbitrary users.

## Release and verify

There is no automatic deployment trigger. The GitHub workflow only tests. For an approved deployment, preserve the source revision, run `make check`, build the API image and scientific runtime, run the additive migration before starting dependent application processes, then restart API and worker. Keep old execution images until their queued/running jobs terminate. Future schema changes require explicit compatible migrations and a backup/recovery plan.

Verify the running API image identity, database health, a real OIDC sign-in, workspace membership denial across two users, a fresh successful run, artifact download, cancellation and an export replay. A successful image build or health query alone does not establish a complete production release. The included local smoke test intentionally does not claim those live checks.

For multiple workers, share PostgreSQL and a private POSIX store. Running attempts are bound to the engine where they started. A worker on another engine may claim queued work but cannot recover an active container by assuming it disappeared. Remote artifact storage, cross-engine failover, and production recovery need an explicit implementation and drill before relying on them.

## Local image check

From the verified macOS profile:

```sh
docker --context colima-research build -f deploy/Dockerfile -t research-workbench-api:local .
uv run python scripts/verify_api_image.py
```

This runs a temporary no-network, non-root API container with ephemeral SQLite, checks health/static UI and the absence of Docker access, writes an evidence receipt, and removes the container. It does not publish a port or alter the running application.
