using System.Security.Claims;
using DocumentReview.Api.Access;
using DocumentReview.Api.Auth;
using DocumentReview.Api.Data;
using DocumentReview.Api.Reviews;
using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore;

namespace DocumentReview.Api.Endpoints;

public sealed record ReviewRequest(ReviewDecision? Decision, string? Comment);

public static class ReviewEndpoints
{
    public static void MapReviewEndpoints(this IEndpointRouteBuilder app)
    {
        var documents = app.MapGroup("/api/documents/{documentId:guid}");
        documents.MapPost("/revisions/{number:int}/reviews", ReviewAsync);
        documents.MapGet("/history", HistoryAsync);
    }

    static async Task<IResult> ReviewAsync(
        Guid documentId,
        int number,
        ReviewRequest request,
        ClaimsPrincipal user,
        ReviewDbContext db,
        WorkspaceAccess access,
        TimeProvider clock,
        CancellationToken cancellationToken)
    {
        var actor = user.Subject();
        var (document, denied) = await access.DocumentAsync(documentId, actor, WorkspaceRole.Reviewer, cancellationToken);
        if (document is null)
        {
            return denied!;
        }

        var problem = ReviewRules.Validate(request.Decision, request.Comment);
        if (problem is not null)
        {
            return Problems.Invalid(problem.Field, problem.Message);
        }

        await using var transaction = await db.Database.BeginTransactionAsync(cancellationToken);

        // Takes the same document lock as uploads, so a decision cannot land on a revision that was just superseded.
        await db.Documents
            .FromSql($"SELECT * FROM Documents WITH (UPDLOCK, HOLDLOCK) WHERE Id = {documentId}")
            .AnyAsync(cancellationToken);
        var revision = await db.DocumentRevisions.SingleOrDefaultAsync(r => r.DocumentId == documentId && r.Number == number, cancellationToken);
        if (revision is null)
        {
            return Problems.NotFound("Revision not found");
        }

        var latest = await db.DocumentRevisions.Where(r => r.DocumentId == documentId).MaxAsync(r => r.Number, cancellationToken);
        if (revision.Number != latest)
        {
            return Problems.Conflict($"Revision {number} was superseded by revision {latest}. Review the latest revision.");
        }

        if (revision.UploadedBy == actor)
        {
            return Results.Problem(statusCode: StatusCodes.Status403Forbidden, title: "Reviewers cannot approve or reject their own revision");
        }

        var review = new RevisionReview
        {
            Id = Guid.NewGuid(),
            RevisionId = revision.Id,
            Reviewer = actor,
            Decision = request.Decision!.Value,
            Comment = string.IsNullOrWhiteSpace(request.Comment) ? null : request.Comment.Trim(),
            ReviewedAt = clock.GetUtcNow(),
        };
        db.RevisionReviews.Add(review);
        try
        {
            await db.SaveChangesAsync(cancellationToken);
        }
        catch (DbUpdateException exception) when (exception.InnerException is SqlException { Number: 2601 or 2627 })
        {
            return Problems.Conflict("You already reviewed this revision");
        }

        await transaction.CommitAsync(cancellationToken);
        return Results.Created(
            $"/api/documents/{documentId}/history",
            new ReviewEntry(review.Reviewer, review.Decision, review.Comment, review.ReviewedAt));
    }

    static async Task<IResult> HistoryAsync(
        Guid documentId, ClaimsPrincipal user, ReviewDbContext db, WorkspaceAccess access, CancellationToken cancellationToken)
    {
        var (document, denied) = await access.DocumentAsync(documentId, user.Subject(), WorkspaceRole.Viewer, cancellationToken);
        if (document is null)
        {
            return denied!;
        }

        var revisions = await db.DocumentRevisions.AsNoTracking().Where(r => r.DocumentId == documentId).ToListAsync(cancellationToken);
        var reviews = await db.RevisionReviews.AsNoTracking()
            .Where(review => db.DocumentRevisions.Any(r => r.Id == review.RevisionId && r.DocumentId == documentId))
            .ToListAsync(cancellationToken);
        return Results.Ok(DocumentHistory.Build(document, revisions, reviews));
    }
}
