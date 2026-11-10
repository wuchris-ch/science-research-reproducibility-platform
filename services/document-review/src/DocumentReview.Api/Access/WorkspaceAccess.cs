using DocumentReview.Api.Data;
using Microsoft.EntityFrameworkCore;

namespace DocumentReview.Api.Access;

public sealed class WorkspaceAccess(ReviewDbContext db)
{
    public async Task<WorkspaceRole?> RoleAsync(Guid workspaceId, string subject, CancellationToken cancellationToken) =>
        await db.WorkspaceMembers
            .Where(m => m.WorkspaceId == workspaceId && m.Subject == subject)
            .Select(m => (WorkspaceRole?)m.Role)
            .SingleOrDefaultAsync(cancellationToken);

    public async Task<bool> HasRoleAsync(Guid workspaceId, string subject, WorkspaceRole minimum, CancellationToken cancellationToken) =>
        await RoleAsync(workspaceId, subject, cancellationToken) >= minimum;
}
