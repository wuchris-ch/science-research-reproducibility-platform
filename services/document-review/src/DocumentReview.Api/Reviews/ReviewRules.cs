using DocumentReview.Api.Data;
using DocumentReview.Api.Documents;

namespace DocumentReview.Api.Reviews;

public enum RevisionStatus
{
    Pending,
    Approved,
    Rejected,
}

public static class ReviewRules
{
    public const int MaxCommentLength = 2000;

    // Any rejection blocks the revision. Otherwise one approval approves it.
    public static RevisionStatus Status(IEnumerable<ReviewDecision> decisions)
    {
        var list = decisions.ToList();
        if (list.Contains(ReviewDecision.Rejected))
        {
            return RevisionStatus.Rejected;
        }

        return list.Contains(ReviewDecision.Approved) ? RevisionStatus.Approved : RevisionStatus.Pending;
    }

    public static UploadProblem? Validate(ReviewDecision? decision, string? comment)
    {
        if (decision is null || !Enum.IsDefined(decision.Value))
        {
            return new UploadProblem("decision", "Decision must be approved or rejected.");
        }

        if (comment?.Length > MaxCommentLength)
        {
            return new UploadProblem("comment", $"Comments must be at most {MaxCommentLength} characters.");
        }

        return decision == ReviewDecision.Rejected && string.IsNullOrWhiteSpace(comment)
            ? new UploadProblem("comment", "Explain what needs to change when rejecting a revision.")
            : null;
    }
}
