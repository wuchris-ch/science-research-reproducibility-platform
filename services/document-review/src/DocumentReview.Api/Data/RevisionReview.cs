namespace DocumentReview.Api.Data;

public enum ReviewDecision
{
    Approved = 1,
    Rejected = 2,
}

// One immutable decision per reviewer per revision.
public sealed class RevisionReview
{
    public Guid Id { get; set; }
    public Guid RevisionId { get; set; }
    public required string Reviewer { get; set; }
    public ReviewDecision Decision { get; set; }
    public string? Comment { get; set; }
    public DateTimeOffset ReviewedAt { get; set; }
}
