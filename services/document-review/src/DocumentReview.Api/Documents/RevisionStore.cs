using System.Security.Cryptography;
using DocumentReview.Api.Data;
using DocumentReview.Api.Storage;
using Microsoft.EntityFrameworkCore;

namespace DocumentReview.Api.Documents;

public sealed record AddRevisionResult(DocumentRevision? Revision, int LatestNumber);

// Uploads the bytes first under a name unique to the revision, then records the metadata in SQL Server.
// If the database write fails or is refused, the blob is deleted so storage keeps no unreferenced files.
public sealed class RevisionStore(ReviewDbContext db, DocumentBlobStore blobs, TimeProvider clock)
{
    public async Task<Document> CreateDocumentAsync(
        Guid workspaceId, string title, IFormFile file, string? note, string actor, CancellationToken cancellationToken)
    {
        var document = new Document { Id = Guid.NewGuid(), WorkspaceId = workspaceId, Title = title.Trim(), CreatedBy = actor, CreatedAt = clock.GetUtcNow() };
        var revision = await UploadAsync(document, file, note, actor, cancellationToken);
        revision.Number = 1;
        document.Revisions.Add(revision);
        db.Documents.Add(document);
        try
        {
            await db.SaveChangesAsync(cancellationToken);
        }
        catch
        {
            await blobs.DeleteAsync(revision.BlobName);
            throw;
        }

        return document;
    }

    public async Task<AddRevisionResult> AddRevisionAsync(
        Document document, IFormFile file, string? note, int? expectedLatestNumber, string actor, CancellationToken cancellationToken)
    {
        var revision = await UploadAsync(document, file, note, actor, cancellationToken);
        try
        {
            await using var transaction = await db.Database.BeginTransactionAsync(cancellationToken);

            // Locks the document row so concurrent uploads take consecutive revision numbers.
            await db.Documents
                .FromSql($"SELECT * FROM Documents WITH (UPDLOCK, HOLDLOCK) WHERE Id = {document.Id}")
                .AnyAsync(cancellationToken);
            var latest = await db.DocumentRevisions.Where(r => r.DocumentId == document.Id).MaxAsync(r => r.Number, cancellationToken);
            if (expectedLatestNumber is not null && expectedLatestNumber != latest)
            {
                await blobs.DeleteAsync(revision.BlobName);
                return new AddRevisionResult(null, latest);
            }

            revision.Number = latest + 1;
            db.DocumentRevisions.Add(revision);
            await db.SaveChangesAsync(cancellationToken);
            await transaction.CommitAsync(cancellationToken);
            return new AddRevisionResult(revision, revision.Number);
        }
        catch
        {
            await blobs.DeleteAsync(revision.BlobName);
            throw;
        }
    }

    async Task<DocumentRevision> UploadAsync(Document document, IFormFile file, string? note, string actor, CancellationToken cancellationToken)
    {
        var revisionId = Guid.NewGuid();
        var contentType = UploadRules.ContentType(file.ContentType);
        string sha256;
        await using (var content = file.OpenReadStream())
        {
            sha256 = Convert.ToHexStringLower(await SHA256.HashDataAsync(content, cancellationToken));
        }

        var blobName = UploadRules.BlobName(document.WorkspaceId, document.Id, revisionId);
        await using (var content = file.OpenReadStream())
        {
            await blobs.UploadAsync(blobName, content, contentType, sha256, cancellationToken);
        }

        return new DocumentRevision
        {
            Id = revisionId,
            DocumentId = document.Id,
            FileName = UploadRules.SafeFileName(file.FileName)!,
            ContentType = contentType,
            SizeBytes = file.Length,
            Sha256 = sha256,
            BlobName = blobName,
            UploadedBy = actor,
            UploadedAt = clock.GetUtcNow(),
            Note = string.IsNullOrWhiteSpace(note) ? null : note.Trim(),
        };
    }
}
