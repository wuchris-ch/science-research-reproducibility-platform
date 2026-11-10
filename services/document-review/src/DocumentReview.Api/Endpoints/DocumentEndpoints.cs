using System.Security.Claims;
using DocumentReview.Api.Access;
using DocumentReview.Api.Auth;
using DocumentReview.Api.Data;
using DocumentReview.Api.Documents;
using DocumentReview.Api.Storage;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;

namespace DocumentReview.Api.Endpoints;

public sealed record RevisionResponse(
    int Number, string FileName, string ContentType, long SizeBytes, string Sha256, string UploadedBy, DateTimeOffset UploadedAt, string? Note)
{
    public static RevisionResponse From(DocumentRevision revision) => new(
        revision.Number, revision.FileName, revision.ContentType, revision.SizeBytes, revision.Sha256, revision.UploadedBy, revision.UploadedAt, revision.Note);
}

public sealed record DocumentResponse(
    Guid Id, Guid WorkspaceId, string Title, string CreatedBy, DateTimeOffset CreatedAt, RevisionResponse LatestRevision);

public static class DocumentEndpoints
{
    public static void MapDocumentEndpoints(this IEndpointRouteBuilder app)
    {
        // Requests authenticate with bearer tokens, not cookies, so form posts need no antiforgery token.
        var workspaceDocuments = app.MapGroup("/api/workspaces/{workspaceId:guid}/documents").DisableAntiforgery();
        workspaceDocuments.MapPost("/", CreateAsync);
        workspaceDocuments.MapGet("/", ListAsync);

        var documents = app.MapGroup("/api/documents/{documentId:guid}").DisableAntiforgery();
        documents.MapGet("/", GetAsync);
        documents.MapPost("/revisions", AddRevisionAsync);
        documents.MapGet("/revisions", ListRevisionsAsync);
        documents.MapGet("/revisions/{number:int}/content", DownloadAsync);
    }

    static async Task<IResult> CreateAsync(
        Guid workspaceId,
        [FromForm] string? title,
        IFormFile? file,
        [FromForm] string? note,
        ClaimsPrincipal user,
        WorkspaceAccess access,
        RevisionStore revisions,
        IOptions<DocumentOptions> options,
        CancellationToken cancellationToken)
    {
        var actor = user.Subject();
        if (!await access.HasRoleAsync(workspaceId, actor, WorkspaceRole.Editor, cancellationToken))
        {
            return Problems.AccessDenied();
        }

        var problem = UploadRules.ValidateTitle(title) ?? UploadRules.Validate(file?.FileName, file?.Length ?? 0, note, options.Value.MaxUploadBytes);
        if (problem is not null)
        {
            return Problems.Invalid(problem.Field, problem.Message);
        }

        var document = await revisions.CreateDocumentAsync(workspaceId, title!, file!, note, actor, cancellationToken);
        return Results.Created($"/api/documents/{document.Id}", ToResponse(document, document.Revisions[0]));
    }

    static async Task<IResult> ListAsync(
        Guid workspaceId, ClaimsPrincipal user, ReviewDbContext db, WorkspaceAccess access, CancellationToken cancellationToken)
    {
        if (!await access.HasRoleAsync(workspaceId, user.Subject(), WorkspaceRole.Viewer, cancellationToken))
        {
            return Problems.AccessDenied();
        }

        var documents = await db.Documents
            .Where(d => d.WorkspaceId == workspaceId)
            .Select(d => new { Document = d, Latest = d.Revisions.OrderByDescending(r => r.Number).First() })
            .ToListAsync(cancellationToken);
        return Results.Ok(documents
            .OrderByDescending(d => d.Latest.UploadedAt)
            .Select(d => ToResponse(d.Document, d.Latest)));
    }

    static async Task<IResult> GetAsync(
        Guid documentId, ClaimsPrincipal user, ReviewDbContext db, WorkspaceAccess access, CancellationToken cancellationToken)
    {
        var (document, denied) = await access.DocumentAsync(documentId, user.Subject(), WorkspaceRole.Viewer, cancellationToken);
        if (document is null)
        {
            return denied!;
        }

        var latest = await db.DocumentRevisions.Where(r => r.DocumentId == documentId).OrderByDescending(r => r.Number).FirstAsync(cancellationToken);
        return Results.Ok(ToResponse(document, latest));
    }

    static async Task<IResult> AddRevisionAsync(
        Guid documentId,
        IFormFile? file,
        [FromForm] string? note,
        [FromForm] int? expectedLatestRevision,
        ClaimsPrincipal user,
        WorkspaceAccess access,
        RevisionStore revisions,
        IOptions<DocumentOptions> options,
        CancellationToken cancellationToken)
    {
        var actor = user.Subject();
        var (document, denied) = await access.DocumentAsync(documentId, actor, WorkspaceRole.Editor, cancellationToken);
        if (document is null)
        {
            return denied!;
        }

        var problem = UploadRules.Validate(file?.FileName, file?.Length ?? 0, note, options.Value.MaxUploadBytes);
        if (problem is not null)
        {
            return Problems.Invalid(problem.Field, problem.Message);
        }

        var result = await revisions.AddRevisionAsync(document, file!, note, expectedLatestRevision, actor, cancellationToken);
        return result.Revision is null
            ? Problems.Conflict($"Revision {result.LatestNumber} is now the latest revision. Review it before uploading again.")
            : Results.Created($"/api/documents/{documentId}/revisions/{result.Revision.Number}", RevisionResponse.From(result.Revision));
    }

    static async Task<IResult> ListRevisionsAsync(
        Guid documentId, ClaimsPrincipal user, ReviewDbContext db, WorkspaceAccess access, CancellationToken cancellationToken)
    {
        var (document, denied) = await access.DocumentAsync(documentId, user.Subject(), WorkspaceRole.Viewer, cancellationToken);
        if (document is null)
        {
            return denied!;
        }

        var revisions = await db.DocumentRevisions.Where(r => r.DocumentId == documentId).OrderBy(r => r.Number).ToListAsync(cancellationToken);
        return Results.Ok(revisions.Select(RevisionResponse.From));
    }

    static async Task<IResult> DownloadAsync(
        Guid documentId,
        int number,
        ClaimsPrincipal user,
        ReviewDbContext db,
        WorkspaceAccess access,
        DocumentBlobStore blobs,
        CancellationToken cancellationToken)
    {
        var (document, denied) = await access.DocumentAsync(documentId, user.Subject(), WorkspaceRole.Viewer, cancellationToken);
        if (document is null)
        {
            return denied!;
        }

        var revision = await db.DocumentRevisions.SingleOrDefaultAsync(r => r.DocumentId == documentId && r.Number == number, cancellationToken);
        if (revision is null)
        {
            return Problems.NotFound("Revision not found");
        }

        var content = await blobs.OpenReadAsync(revision.BlobName, cancellationToken);
        return Results.Stream(content, revision.ContentType, revision.FileName);
    }

    static DocumentResponse ToResponse(Document document, DocumentRevision latest) =>
        new(document.Id, document.WorkspaceId, document.Title, document.CreatedBy, document.CreatedAt, RevisionResponse.From(latest));
}
