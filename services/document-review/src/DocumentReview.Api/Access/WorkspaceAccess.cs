using DocumentReview.Api.Data;
using DocumentReview.Api.Endpoints;
using Microsoft.EntityFrameworkCore;

namespace DocumentReview.Api.Access;

public sealed record DocumentAccess(Document? Document, IResult? Denied);

public sealed class WorkspaceAccess(ReviewDbContext db)
{
    public async Task<WorkspaceRole?> RoleAsync(Guid workspaceId, string subject, CancellationToken cancellationToken) =>
        await db.WorkspaceMembers
            .Where(m => m.WorkspaceId == workspaceId && m.Subject == subject)
            .Select(m => (WorkspaceRole?)m.Role)
            .SingleOrDefaultAsync(cancellationToken);

    public async Task<bool> HasRoleAsync(Guid workspaceId, string subject, WorkspaceRole minimum, CancellationToken cancellationToken) =>
        await RoleAsync(workspaceId, subject, cancellationToken) >= minimum;

    // Callers outside the workspace get 404 so document IDs do not reveal which documents exist.
    // Members without the required role get 403.
    public async Task<DocumentAccess> DocumentAsync(Guid documentId, string subject, WorkspaceRole minimum, CancellationToken cancellationToken)
    {
        var document = await db.Documents.AsNoTracking().SingleOrDefaultAsync(d => d.Id == documentId, cancellationToken);
        var role = document is null ? null : await RoleAsync(document.WorkspaceId, subject, cancellationToken);
        if (document is null || role is null)
        {
            return new DocumentAccess(null, Problems.NotFound("Document not found"));
        }

        return role >= minimum ? new DocumentAccess(document, null) : new DocumentAccess(null, Problems.AccessDenied());
    }
}
