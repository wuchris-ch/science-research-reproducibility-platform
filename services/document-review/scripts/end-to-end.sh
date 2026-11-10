#!/usr/bin/env bash
# Exercises a running document review API end to end and prints a transcript.
# Start SQL Server, Azurite and the API first (see README.md), then run:
#   scripts/end-to-end.sh | tee ../../evidence/document-review-end-to-end.txt
set -euo pipefail
cd "$(dirname "$0")/.."

api="${REVIEW_API:-http://127.0.0.1:8319}"
sql_container="${REVIEW_SQL_CONTAINER:-review-sql}"
azurite_container="${REVIEW_AZURITE_CONTAINER:-review-azurite}"
sql_password="${REVIEW_SQL_PASSWORD:-Review_Local_2026!}"
database="${REVIEW_DATABASE:-DocumentReview}"
work="$(mktemp -d)"

step() { printf '\n## %s\n\n' "$*"; }

# call METHOD PATH TOKEN [curl arguments]: prints the request, status and JSON body; the body stays in $work/body.
call() {
  local method=$1 path=$2 bearer=$3
  shift 3
  printf '> %s %s\n' "$method" "$path"
  local status
  status=$(curl -sS -o "$work/body" -w '%{http_code}' -X "$method" -H "Authorization: Bearer $bearer" "$@" "$api$path")
  printf '< %s\n' "$status"
  if [ -s "$work/body" ]; then jq . "$work/body"; fi
  printf '\n'
}

sql() {
  docker exec "$sql_container" /opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P "$sql_password" -d "$database" -W -s ' | ' -Q "SET NOCOUNT ON; $1"
}

step "Environment"
printf 'Run at: %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
printf 'Commit: %s\n' "$(git rev-parse --short HEAD)"
printf '.NET SDK: %s\n' "$(dotnet --version)"
printf 'SQL Server: %s\n' "$(sql "SELECT CAST(SERVERPROPERTY('ProductVersion') AS nvarchar(32)) + ' ' + CAST(SERVERPROPERTY('Edition') AS nvarchar(64))" | tail -1)"
printf 'Azurite: %s\n' "$(docker exec "$azurite_container" azurite --version)"

# dotnet run prints a launch settings line first; the token is the last line.
ada=$(dotnet run --no-build --project src/DocumentReview.Api -- issue-token ada | tail -1)
grace=$(dotnet run --no-build --project src/DocumentReview.Api -- issue-token grace | tail -1)
printf 'Issued local development tokens for ada (author) and grace (reviewer).\n'

step "Health"
curl -sS "$api/healthz" | jq .

step "Create a workspace and add a reviewer"
call POST /api/workspaces "$ada" -H 'Content-Type: application/json' -d '{"name":"Airway study review"}'
workspace=$(jq -er .id "$work/body")
call PUT "/api/workspaces/$workspace/members" "$ada" -H 'Content-Type: application/json' -d '{"subject":"grace","role":"reviewer"}'

step "Upload the first revision"
printf '# Methods appendix\n\nFilter: CPM > 0.5 in at least 2 samples.\n' > "$work/methods-v1.md"
printf 'Local SHA-256: %s\n\n' "$(shasum -a 256 "$work/methods-v1.md" | cut -d' ' -f1)"
call POST "/api/workspaces/$workspace/documents" "$ada" -F 'title=Airway methods appendix' -F "file=@$work/methods-v1.md;type=text/markdown"
document=$(jq -er .id "$work/body")

step "Upload the second revision"
printf '# Methods appendix\n\nFilter: CPM > 1 in at least 3 samples.\nDesign: ~ donor + treatment.\n' > "$work/methods-v2.md"
printf 'Local SHA-256: %s\n\n' "$(shasum -a 256 "$work/methods-v2.md" | cut -d' ' -f1)"
call POST "/api/documents/$document/revisions" "$ada" -F "file=@$work/methods-v2.md;type=text/markdown" -F 'note=Stricter filter and paired design' -F 'expectedLatestRevision=1'

step "Rules: the superseded revision and the author's own revision cannot be approved"
call POST "/api/documents/$document/revisions/1/reviews" "$grace" -H 'Content-Type: application/json' -d '{"decision":"approved"}'
call POST "/api/documents/$document/revisions/2/reviews" "$ada" -H 'Content-Type: application/json' -d '{"decision":"approved"}'

step "Approve revision 2"
call POST "/api/documents/$document/revisions/2/reviews" "$grace" -H 'Content-Type: application/json' -d '{"decision":"approved","comment":"Filter and design match the source paper."}'

step "Read the history back"
call GET "/api/documents/$document/history" "$grace"

step "Download revision 2 from Blob Storage through the API"
curl -sS -H "Authorization: Bearer $grace" -o "$work/downloaded.md" "$api/api/documents/$document/revisions/2/content"
printf 'Downloaded SHA-256: %s\n' "$(shasum -a 256 "$work/downloaded.md" | cut -d' ' -f1)"
printf 'Matches the uploaded file: %s\n' "$(cmp -s "$work/downloaded.md" "$work/methods-v2.md" && echo yes || echo no)"

step "SQL Server rows (metadata and blob names only)"
sql "SELECT MigrationId FROM __EFMigrationsHistory ORDER BY MigrationId"
printf '\n'
sql "SELECT r.Number, r.FileName, r.SizeBytes, r.Sha256, r.BlobName, r.UploadedBy FROM DocumentRevisions r WHERE r.DocumentId = '$document' ORDER BY r.Number"
printf '\n'
sql "SELECT r.Number, v.Reviewer, v.Decision, v.Comment FROM RevisionReviews v JOIN DocumentRevisions r ON r.Id = v.RevisionId WHERE r.DocumentId = '$document'"
printf '\n'
sql "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'DocumentRevisions' ORDER BY ORDINAL_POSITION"

step "Azurite blob writes for this document"
docker logs "$azurite_container" 2>&1 | grep 'PUT' | grep "$(echo "$document" | tr -d '-')" || true
