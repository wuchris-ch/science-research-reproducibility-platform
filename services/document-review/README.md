# Document review service

An ASP.NET Core Web API for reviewing the documents behind a study. It stores document metadata in SQL Server through Entity Framework Core and keeps file bytes in Azure Blob Storage. It runs beside the Python workbench and uses the same workspace roles: owner, editor, reviewer and viewer.

## Run locally

Requires the .NET 10 SDK and a Docker engine. On Apple Silicon, SQL Server runs as `linux/amd64`; the `research` Colima profile from the main README uses Rosetta for this.

```sh
docker run -d --name review-sql --platform linux/amd64 -e ACCEPT_EULA=Y -e MSSQL_SA_PASSWORD='Review_Local_2026!' -p 1433:1433 mcr.microsoft.com/mssql/server:2022-latest
docker run -d --name review-azurite -p 10000:10000 mcr.microsoft.com/azure-storage/azurite azurite-blob --blobHost 0.0.0.0 --skipApiVersionCheck
dotnet run --project src/DocumentReview.Api
```

The Development profile listens on http://127.0.0.1:8319, applies migrations and creates the blob container on startup. Azurite needs `--skipApiVersionCheck` when the Blob Storage SDK is newer than the emulator.

Requests need a bearer token with a `sub` claim. For local development, print a token signed with the development key:

```sh
dotnet run --project src/DocumentReview.Api -- issue-token ada
```

A team installation sets `Auth__Authority` and `Auth__Audience` to its OIDC issuer instead of `Auth__LocalSigningKey`. The service then validates RS256 tokens from the issuer's discovery document.

## Endpoints

| Method and path | Minimum role | Behavior |
|---|---|---|
| `GET /healthz` | None | Checks SQL Server and the blob container |
| `POST /api/workspaces` | Signed in | Creates a workspace; the caller becomes its owner |
| `GET /api/workspaces` | Signed in | Lists the caller's workspaces and roles |
| `GET /api/workspaces/{id}/members` | viewer | Lists members |
| `PUT /api/workspaces/{id}/members` | owner | Adds a member or changes a role; the last owner cannot be demoted |
| `POST /api/workspaces/{id}/documents` | editor | Multipart `title`, `file` and optional `note`; creates a document with revision 1 |
| `GET /api/workspaces/{id}/documents` | viewer | Lists documents with their latest revision |
| `GET /api/documents/{id}` | viewer | Returns a document and its latest revision |
| `POST /api/documents/{id}/revisions` | editor | Multipart `file`, optional `note` and `expectedLatestRevision`; adds the next revision |
| `GET /api/documents/{id}/revisions` | viewer | Lists every revision with size, SHA-256, uploader and note |
| `GET /api/documents/{id}/revisions/{number}/content` | viewer | Streams the revision's file from Blob Storage |

Callers outside a workspace get 404 for its documents, so document IDs do not reveal which documents exist. Members without the required role get 403.

## Storage

Each upload is hashed with SHA-256 and written to the blob `{workspace}/{document}/{revision}` with an if-none-match condition, so an existing blob is never overwritten. SQL Server then records the revision metadata and blob name in one transaction. The transaction locks the document row, so concurrent uploads take consecutive revision numbers. If the database write fails, or `expectedLatestRevision` no longer matches, the service deletes the new blob. Uploads are limited to `Documents:MaxUploadBytes` (25 MiB by default). File names keep only their last path segment.

## Test

```sh
dotnet test
```

The integration tests start the API in memory and use real SQL Server and Azurite. Each test class creates its own database and blob container and deletes them afterwards. Set `DOCUMENT_REVIEW_TEST_SQL` and `DOCUMENT_REVIEW_TEST_BLOBS` to use other servers. The GitHub workflow `document-review.yml` runs the same tests with SQL Server and Azurite containers, and it fails on formatting changes or an entity model change without a migration.
