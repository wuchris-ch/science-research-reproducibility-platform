using DocumentReview.Api.Data;

namespace DocumentReview.Tests;

public class WorkspaceRoleTests
{
    [Theory]
    [InlineData(WorkspaceRole.Owner, 4)]
    [InlineData(WorkspaceRole.Editor, 3)]
    [InlineData(WorkspaceRole.Reviewer, 2)]
    [InlineData(WorkspaceRole.Viewer, 1)]
    public void Ranks_match_the_workbench_roles(WorkspaceRole role, int rank) =>
        Assert.Equal(rank, (int)role);

    [Fact]
    public void Editors_outrank_reviewers_so_they_can_also_review() =>
        Assert.True(WorkspaceRole.Editor >= WorkspaceRole.Reviewer);
}
