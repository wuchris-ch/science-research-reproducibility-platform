using Microsoft.EntityFrameworkCore;

namespace DocumentReview.Api.Data;

public sealed class ReviewDbContext(DbContextOptions<ReviewDbContext> options) : DbContext(options)
{
    public DbSet<Workspace> Workspaces => Set<Workspace>();
    public DbSet<WorkspaceMember> WorkspaceMembers => Set<WorkspaceMember>();
    public DbSet<Document> Documents => Set<Document>();
    public DbSet<DocumentRevision> DocumentRevisions => Set<DocumentRevision>();

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

        modelBuilder.Entity<Document>(document =>
        {
            document.Property(d => d.Title).HasMaxLength(300);
            document.Property(d => d.CreatedBy).HasMaxLength(200);
            document.HasIndex(d => d.WorkspaceId);
            document.HasOne<Workspace>().WithMany().HasForeignKey(d => d.WorkspaceId).OnDelete(DeleteBehavior.Restrict);
            document.HasMany(d => d.Revisions).WithOne().HasForeignKey(r => r.DocumentId).OnDelete(DeleteBehavior.Restrict);
        });

        modelBuilder.Entity<DocumentRevision>(revision =>
        {
            revision.HasIndex(r => new { r.DocumentId, r.Number }).IsUnique();
            revision.HasIndex(r => r.BlobName).IsUnique();
            revision.Property(r => r.FileName).HasMaxLength(255);
            revision.Property(r => r.ContentType).HasMaxLength(200).IsUnicode(false);
            revision.Property(r => r.Sha256).HasMaxLength(64).IsFixedLength().IsUnicode(false);
            revision.Property(r => r.BlobName).HasMaxLength(300).IsUnicode(false);
            revision.Property(r => r.UploadedBy).HasMaxLength(200);
            revision.Property(r => r.Note).HasMaxLength(2000);
        });
    }
}
