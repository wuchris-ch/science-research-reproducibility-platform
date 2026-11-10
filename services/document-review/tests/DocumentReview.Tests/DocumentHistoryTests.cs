using DocumentReview.Api.Data;
using DocumentReview.Api.Reviews;

namespace DocumentReview.Tests;

public class DocumentHistoryTests
{
    static readonly DateTimeOffset Start = new(2026, 11, 9, 12, 0, 0, TimeSpan.Zero);

    static DocumentRevision Revision(Guid documentId, int number, string uploader, int minute) => new()
    {
        Id = Guid.NewGuid(),
        DocumentId = documentId,
        Number = number,
        FileName = $"draft-{number}.pdf",
        ContentType = "application/pdf",
        SizeBytes = 10,
        Sha256 = new string('a', 64),
        BlobName = $"blob-{number}",
        UploadedBy = uploader,
        UploadedAt = Start.AddMinutes(minute),
    };

    [Fact]
    public void Builds_revision_statuses_and_a_chronological_timeline()
    {
        var document = new Document { Id = Guid.NewGuid(), WorkspaceId = Guid.NewGuid(), Title = "Methods", CreatedBy = "ada", CreatedAt = Start };
        var first = Revision(document.Id, 1, "ada", 0);
        var second = Revision(document.Id, 2, "ada", 10);
        var reviews = new List<RevisionReview>
        {
            new() { Id = Guid.NewGuid(), RevisionId = second.Id, Reviewer = "grace", Decision = ReviewDecision.Approved, ReviewedAt = Start.AddMinutes(20) },
            new() { Id = Guid.NewGuid(), RevisionId = first.Id, Reviewer = "linus", Decision = ReviewDecision.Rejected, Comment = "Missing filter", ReviewedAt = Start.AddMinutes(5) },
        };

        var history = DocumentHistory.Build(document, [second, first], reviews);

        Assert.Equal([1, 2], history.Revisions.Select(r => r.Number));
        Assert.Equal([RevisionStatus.Rejected, RevisionStatus.Approved], history.Revisions.Select(r => r.Status));
        Assert.Equal([false, true], history.Revisions.Select(r => r.IsLatest));
        Assert.Equal(
            ["uploaded 1 ada", "rejected 1 linus", "uploaded 2 ada", "approved 2 grace"],
            history.Events.Select(e => $"{e.Kind} {e.Revision} {e.Actor}"));
        Assert.Equal("Missing filter", history.Events[1].Detail);
    }
}
