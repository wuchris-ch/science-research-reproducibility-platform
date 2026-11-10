using DocumentReview.Api.Data;

namespace DocumentReview.Api.Reviews;

public sealed record ReviewEntry(string Reviewer, ReviewDecision Decision, string? Comment, DateTimeOffset ReviewedAt);

public sealed record RevisionHistory(
    int Number,
    string FileName,
    string ContentType,
    long SizeBytes,
    string Sha256,
    string UploadedBy,
    DateTimeOffset UploadedAt,
    string? Note,
    bool IsLatest,
    RevisionStatus Status,
    IReadOnlyList<ReviewEntry> Reviews);

public sealed record HistoryEvent(DateTimeOffset At, string Actor, string Kind, int Revision, string? Detail);

public sealed record DocumentHistoryResponse(
    Guid Id, Guid WorkspaceId, string Title, string CreatedBy, DateTimeOffset CreatedAt, IReadOnlyList<RevisionHistory> Revisions, IReadOnlyList<HistoryEvent> Events);

public static class DocumentHistory
{
    // Builds the per-revision view and one chronological timeline of uploads and decisions.
    public static DocumentHistoryResponse Build(Document document, IReadOnlyList<DocumentRevision> revisions, IReadOnlyList<RevisionReview> reviews)
    {
        var latest = revisions.Count == 0 ? 0 : revisions.Max(r => r.Number);
        var reviewsByRevision = reviews.ToLookup(r => r.RevisionId);
        var revisionNumbers = revisions.ToDictionary(r => r.Id, r => r.Number);

        var revisionHistory = revisions
            .OrderBy(r => r.Number)
            .Select(r =>
            {
                var entries = reviewsByRevision[r.Id]
                    .OrderBy(review => review.ReviewedAt)
                    .Select(review => new ReviewEntry(review.Reviewer, review.Decision, review.Comment, review.ReviewedAt))
                    .ToList();
                return new RevisionHistory(
                    r.Number, r.FileName, r.ContentType, r.SizeBytes, r.Sha256, r.UploadedBy, r.UploadedAt, r.Note,
                    r.Number == latest, ReviewRules.Status(entries.Select(e => e.Decision)), entries);
            })
            .ToList();

        var uploads = revisions.Select(r => new HistoryEvent(r.UploadedAt, r.UploadedBy, "uploaded", r.Number, r.Note));
        var decisions = reviews.Select(r => new HistoryEvent(
            r.ReviewedAt, r.Reviewer, r.Decision == ReviewDecision.Approved ? "approved" : "rejected", revisionNumbers[r.RevisionId], r.Comment));
        var events = uploads.Concat(decisions)
            .OrderBy(e => e.At)
            .ThenBy(e => e.Revision)
            .ThenBy(e => e.Kind == "uploaded" ? 0 : 1)
            .ToList();

        return new DocumentHistoryResponse(
            document.Id, document.WorkspaceId, document.Title, document.CreatedBy, document.CreatedAt, revisionHistory, events);
    }
}
