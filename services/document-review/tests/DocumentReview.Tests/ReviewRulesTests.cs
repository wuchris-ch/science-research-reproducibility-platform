using DocumentReview.Api.Data;
using DocumentReview.Api.Reviews;

namespace DocumentReview.Tests;

public class ReviewRulesTests
{
    [Theory]
    [InlineData(new ReviewDecision[0], RevisionStatus.Pending)]
    [InlineData(new[] { ReviewDecision.Approved }, RevisionStatus.Approved)]
    [InlineData(new[] { ReviewDecision.Approved, ReviewDecision.Approved }, RevisionStatus.Approved)]
    [InlineData(new[] { ReviewDecision.Approved, ReviewDecision.Rejected }, RevisionStatus.Rejected)]
    [InlineData(new[] { ReviewDecision.Rejected }, RevisionStatus.Rejected)]
    public void Any_rejection_blocks_a_revision(ReviewDecision[] decisions, RevisionStatus expected) =>
        Assert.Equal(expected, ReviewRules.Status(decisions));

    [Fact]
    public void Approval_needs_no_comment() =>
        Assert.Null(ReviewRules.Validate(ReviewDecision.Approved, null));

    [Theory]
    [InlineData(null)]
    [InlineData("  ")]
    public void Rejection_needs_a_comment(string? comment) =>
        Assert.Equal("comment", ReviewRules.Validate(ReviewDecision.Rejected, comment)?.Field);

    [Fact]
    public void Decision_is_required() =>
        Assert.Equal("decision", ReviewRules.Validate(null, "Looks good")?.Field);

    [Fact]
    public void Long_comments_are_rejected() =>
        Assert.Equal("comment", ReviewRules.Validate(ReviewDecision.Approved, new string('x', ReviewRules.MaxCommentLength + 1))?.Field);
}
