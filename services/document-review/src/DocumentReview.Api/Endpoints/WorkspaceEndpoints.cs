using System.Security.Claims;
using DocumentReview.Api.Access;
using DocumentReview.Api.Auth;
using DocumentReview.Api.Data;
using Microsoft.EntityFrameworkCore;

namespace DocumentReview.Api.Endpoints;

public sealed record CreateWorkspaceRequest(string? Name);

public sealed record WorkspaceResponse(Guid Id, string Name, WorkspaceRole Role, string CreatedBy, DateTimeOffset CreatedAt);

public sealed record SetMemberRequest(string? Subject, WorkspaceRole? Role);

public sealed record MemberResponse(string Subject, WorkspaceRole Role, string AssignedBy, DateTimeOffset AssignedAt);

public static class WorkspaceEndpoints
{
    public static void MapWorkspaceEndpoints(this IEndpointRouteBuilder app)
    {
        var workspaces = app.MapGroup("/api/workspaces");
        workspaces.MapPost("/", CreateAsync);
        workspaces.MapGet("/", ListAsync);
        workspaces.MapGet("/{workspaceId:guid}/members", ListMembersAsync);
        workspaces.MapPut("/{workspaceId:guid}/members", SetMemberAsync);
    }

    static async Task<IResult> CreateAsync(
        CreateWorkspaceRequest request, ClaimsPrincipal user, ReviewDbContext db, TimeProvider clock, CancellationToken cancellationToken)
    {
        var name = request.Name?.Trim();
        if (string.IsNullOrEmpty(name) || name.Length > 200)
        {
            return Problems.Invalid("name", "Name must be 1 to 200 characters.");
        }

        var actor = user.Subject();
        var now = clock.GetUtcNow();
        var workspace = new Workspace { Id = Guid.NewGuid(), Name = name, CreatedBy = actor, CreatedAt = now };
        workspace.Members.Add(new WorkspaceMember { Subject = actor, Role = WorkspaceRole.Owner, AssignedBy = actor, AssignedAt = now });
        db.Workspaces.Add(workspace);
        await db.SaveChangesAsync(cancellationToken);
        return Results.Created(
            $"/api/workspaces/{workspace.Id}",
            new WorkspaceResponse(workspace.Id, workspace.Name, WorkspaceRole.Owner, actor, now));
    }

    static async Task<IResult> ListAsync(ClaimsPrincipal user, ReviewDbContext db, CancellationToken cancellationToken)
    {
        var actor = user.Subject();
        var rows = await db.WorkspaceMembers
            .Where(m => m.Subject == actor)
            .Join(db.Workspaces, m => m.WorkspaceId, w => w.Id, (m, w) => new { w.Id, w.Name, m.Role, w.CreatedBy, w.CreatedAt })
            .ToListAsync(cancellationToken);
        return Results.Ok(rows
            .OrderByDescending(w => w.CreatedAt)
            .Select(w => new WorkspaceResponse(w.Id, w.Name, w.Role, w.CreatedBy, w.CreatedAt)));
    }

    static async Task<IResult> ListMembersAsync(
        Guid workspaceId, ClaimsPrincipal user, ReviewDbContext db, WorkspaceAccess access, CancellationToken cancellationToken)
    {
        if (!await access.HasRoleAsync(workspaceId, user.Subject(), WorkspaceRole.Viewer, cancellationToken))
        {
            return Problems.AccessDenied();
        }

        var members = await db.WorkspaceMembers
            .Where(m => m.WorkspaceId == workspaceId)
            .OrderBy(m => m.Subject)
            .Select(m => new MemberResponse(m.Subject, m.Role, m.AssignedBy, m.AssignedAt))
            .ToListAsync(cancellationToken);
        return Results.Ok(members);
    }

    static async Task<IResult> SetMemberAsync(
        Guid workspaceId,
        SetMemberRequest request,
        ClaimsPrincipal user,
        ReviewDbContext db,
        WorkspaceAccess access,
        TimeProvider clock,
        CancellationToken cancellationToken)
    {
        var subject = request.Subject?.Trim();
        if (string.IsNullOrEmpty(subject) || subject.Length > 200)
        {
            return Problems.Invalid("subject", "Subject must be 1 to 200 characters.");
        }

        if (request.Role is not { } role || !Enum.IsDefined(role))
        {
            return Problems.Invalid("role", "Role must be owner, editor, reviewer or viewer.");
        }

        var actor = user.Subject();
        await using var transaction = await db.Database.BeginTransactionAsync(cancellationToken);

        // Serializes membership changes per workspace so two owners cannot demote each other at the same time.
        var locked = await db.Workspaces
            .FromSql($"SELECT * FROM Workspaces WITH (UPDLOCK, HOLDLOCK) WHERE Id = {workspaceId}")
            .AnyAsync(cancellationToken);
        if (!locked || !await access.HasRoleAsync(workspaceId, actor, WorkspaceRole.Owner, cancellationToken))
        {
            return Problems.AccessDenied();
        }

        var member = await db.WorkspaceMembers.SingleOrDefaultAsync(m => m.WorkspaceId == workspaceId && m.Subject == subject, cancellationToken);
        if (member?.Role == WorkspaceRole.Owner && role != WorkspaceRole.Owner)
        {
            var owners = await db.WorkspaceMembers.CountAsync(m => m.WorkspaceId == workspaceId && m.Role == WorkspaceRole.Owner, cancellationToken);
            if (owners <= 1)
            {
                return Problems.Conflict("Workspace must retain an owner");
            }
        }

        if (member is null)
        {
            member = new WorkspaceMember { WorkspaceId = workspaceId, Subject = subject, AssignedBy = actor };
            db.WorkspaceMembers.Add(member);
        }

        member.Role = role;
        member.AssignedBy = actor;
        member.AssignedAt = clock.GetUtcNow();
        await db.SaveChangesAsync(cancellationToken);
        await transaction.CommitAsync(cancellationToken);
        return Results.Ok(new MemberResponse(member.Subject, member.Role, member.AssignedBy, member.AssignedAt));
    }
}
