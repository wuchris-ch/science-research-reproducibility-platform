using System.Net;
using System.Text;
using DocumentReview.Api.Data;
using DocumentReview.Api.Reviews;

namespace DocumentReview.Tests;

public class ReviewApiTests(ReviewApiFactory api) : IClassFixture<ReviewApiFactory>
{
    static byte[] Bytes(string text) => Encoding.UTF8.GetBytes(text);

    async Task<(HttpClient Author, HttpClient Reviewer, Guid DocumentId)> DocumentWithReviewerAsync(string author, string reviewer)
    {
        var authorClient = api.ClientFor(author);
        var workspace = await authorClient.CreateWorkspaceAsync((reviewer, "reviewer"), ("viewer-" + author, "viewer"));
        var document = await authorClient.CreateDocumentAsync(workspace.Id, Bytes("draft one"));
        return (authorClient, api.ClientFor(reviewer), document.Id);
    }

    [Fact]
    public async Task Reviewers_see_each_revision_with_its_approvals()
    {
        var (author, reviewer, documentId) = await DocumentWithReviewerAsync("ada", "grace");
        (await author.PostAsync($"/api/documents/{documentId}/revisions", ApiClient.Upload("v2.pdf", Bytes("draft two"), fields: ("note", "Fixes table 2")))).EnsureSuccessStatusCode();

        var approval = await reviewer.PostJsonAsync($"/api/documents/{documentId}/revisions/2/reviews", new { decision = "approved", comment = "Matches the source" });
        var history = await (await api.ClientFor("viewer-ada").GetAsync($"/api/documents/{documentId}/history")).ReadAsync<DocumentHistoryResponse>();

        Assert.Equal(HttpStatusCode.Created, approval.StatusCode);
        Assert.Equal([RevisionStatus.Pending, RevisionStatus.Approved], history.Revisions.Select(r => r.Status));
        Assert.Equal([false, true], history.Revisions.Select(r => r.IsLatest));
        var review = Assert.Single(history.Revisions[1].Reviews);
        Assert.Equal(("grace", ReviewDecision.Approved, "Matches the source"), (review.Reviewer, review.Decision, review.Comment));
        Assert.Equal(["uploaded 1 ada", "uploaded 2 ada", "approved 2 grace"], history.Events.Select(e => $"{e.Kind} {e.Revision} {e.Actor}"));
    }

    [Fact]
    public async Task Rejection_requires_a_comment_and_marks_the_revision_rejected()
    {
        var (_, reviewer, documentId) = await DocumentWithReviewerAsync("barbara", "ken");
        var reviews = $"/api/documents/{documentId}/revisions/1/reviews";

        var withoutComment = await reviewer.PostJsonAsync(reviews, new { decision = "rejected" });
        var withComment = await reviewer.PostJsonAsync(reviews, new { decision = "rejected", comment = "The sample table is missing." });
        var history = await (await reviewer.GetAsync($"/api/documents/{documentId}/history")).ReadAsync<DocumentHistoryResponse>();

        Assert.Equal(HttpStatusCode.BadRequest, withoutComment.StatusCode);
        Assert.Equal(HttpStatusCode.Created, withComment.StatusCode);
        Assert.Equal(RevisionStatus.Rejected, history.Revisions[0].Status);
    }

    [Fact]
    public async Task Authors_viewers_and_outsiders_cannot_review()
    {
        var (author, _, documentId) = await DocumentWithReviewerAsync("linus", "radia");
        var reviews = $"/api/documents/{documentId}/revisions/1/reviews";
        var approval = new { decision = "approved" };

        Assert.Equal(HttpStatusCode.Forbidden, (await author.PostJsonAsync(reviews, approval)).StatusCode);
        Assert.Equal(HttpStatusCode.Forbidden, (await api.ClientFor("viewer-linus").PostJsonAsync(reviews, approval)).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await api.ClientFor("eve").PostJsonAsync(reviews, approval)).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await api.ClientFor("eve").GetAsync($"/api/documents/{documentId}/history")).StatusCode);
    }

    [Fact]
    public async Task Superseded_revisions_cannot_be_reviewed()
    {
        var (author, reviewer, documentId) = await DocumentWithReviewerAsync("frances", "john");
        (await author.PostAsync($"/api/documents/{documentId}/revisions", ApiClient.Upload("v2.pdf", Bytes("two")))).EnsureSuccessStatusCode();

        var response = await reviewer.PostJsonAsync($"/api/documents/{documentId}/revisions/1/reviews", new { decision = "approved" });

        Assert.Equal(HttpStatusCode.Conflict, response.StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await reviewer.PostJsonAsync($"/api/documents/{documentId}/revisions/9/reviews", new { decision = "approved" })).StatusCode);
    }

    [Fact]
    public async Task Each_reviewer_records_one_decision_per_revision_even_under_concurrency()
    {
        var (_, reviewer, documentId) = await DocumentWithReviewerAsync("margaret", "edsger");
        var reviews = $"/api/documents/{documentId}/revisions/1/reviews";

        var responses = await Task.WhenAll(Enumerable.Range(0, 5).Select(_ => reviewer.PostJsonAsync(reviews, new { decision = "approved" })));
        var history = await (await reviewer.GetAsync($"/api/documents/{documentId}/history")).ReadAsync<DocumentHistoryResponse>();

        Assert.Single(responses, r => r.StatusCode == HttpStatusCode.Created);
        Assert.All(responses.Where(r => r.StatusCode != HttpStatusCode.Created), r => Assert.Equal(HttpStatusCode.Conflict, r.StatusCode));
        Assert.Single(history.Revisions[0].Reviews);
    }

    [Fact]
    public async Task Editors_can_review_revisions_they_did_not_upload()
    {
        var owner = api.ClientFor("tim");
        var workspace = await owner.CreateWorkspaceAsync(("sophie", "editor"));
        var document = await owner.CreateDocumentAsync(workspace.Id, Bytes("draft"));

        var response = await api.ClientFor("sophie").PostJsonAsync($"/api/documents/{document.Id}/revisions/1/reviews", new { decision = "approved" });

        Assert.Equal(HttpStatusCode.Created, response.StatusCode);
    }
}
