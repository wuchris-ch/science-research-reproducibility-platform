namespace DocumentReview.Api.Data;

public sealed class Document
{
    public Guid Id { get; set; }
    public Guid WorkspaceId { get; set; }
    public required string Title { get; set; }
    public required string CreatedBy { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public List<DocumentRevision> Revisions { get; set; } = [];
}

// Revisions are immutable. Number counts from 1 within a document. The file bytes are in Blob Storage under BlobName.
public sealed class DocumentRevision
{
    public Guid Id { get; set; }
    public Guid DocumentId { get; set; }
    public int Number { get; set; }
    public required string FileName { get; set; }
    public required string ContentType { get; set; }
    public long SizeBytes { get; set; }
    public required string Sha256 { get; set; }
    public required string BlobName { get; set; }
    public required string UploadedBy { get; set; }
    public DateTimeOffset UploadedAt { get; set; }
    public string? Note { get; set; }
}
