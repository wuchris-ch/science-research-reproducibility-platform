namespace DocumentReview.Api.Data;

// Same names and ranks as the workbench API: owner 4, editor 3, reviewer 2, viewer 1.
public enum WorkspaceRole
{
    Viewer = 1,
    Reviewer = 2,
    Editor = 3,
    Owner = 4,
}

public sealed class Workspace
{
    public Guid Id { get; set; }
    public required string Name { get; set; }
    public required string CreatedBy { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
    public List<WorkspaceMember> Members { get; set; } = [];
}

public sealed class WorkspaceMember
{
    public Guid WorkspaceId { get; set; }
    public required string Subject { get; set; }
    public WorkspaceRole Role { get; set; }
    public required string AssignedBy { get; set; }
    public DateTimeOffset AssignedAt { get; set; }
}
