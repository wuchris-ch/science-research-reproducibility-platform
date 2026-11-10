using Microsoft.EntityFrameworkCore;

namespace DocumentReview.Api.Data;

public sealed class ReviewDbContext(DbContextOptions<ReviewDbContext> options) : DbContext(options)
{
    public DbSet<Workspace> Workspaces => Set<Workspace>();
    public DbSet<WorkspaceMember> WorkspaceMembers => Set<WorkspaceMember>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<Workspace>(workspace =>
        {
            workspace.Property(w => w.Name).HasMaxLength(200);
            workspace.Property(w => w.CreatedBy).HasMaxLength(200);
            workspace.HasMany(w => w.Members).WithOne().HasForeignKey(m => m.WorkspaceId);
        });

        modelBuilder.Entity<WorkspaceMember>(member =>
        {
            member.HasKey(m => new { m.WorkspaceId, m.Subject });
            member.HasIndex(m => m.Subject);
            member.Property(m => m.Subject).HasMaxLength(200);
            member.Property(m => m.AssignedBy).HasMaxLength(200);
            member.Property(m => m.Role)
                .HasConversion(role => role.ToString().ToLowerInvariant(), value => Enum.Parse<WorkspaceRole>(value, true))
                .HasMaxLength(16);
        });
    }
}
