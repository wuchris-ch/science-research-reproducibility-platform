using System.Net;
using System.Net.Http.Headers;
using DocumentReview.Api.Auth;
using DocumentReview.Api.Data;
using DocumentReview.Api.Endpoints;

namespace DocumentReview.Tests;

public class WorkspaceApiTests(ReviewApiFactory api) : IClassFixture<ReviewApiFactory>
{
    [Fact]
    public async Task Health_reports_sql_server_and_blob_storage()
    {
        var response = await api.CreateClient().GetAsync("/healthz");

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        Assert.Equal("""{"database":"ok","blobStorage":"ok"}""", await response.Content.ReadAsStringAsync());
    }

    [Fact]
    public async Task Requests_without_a_valid_token_are_rejected()
    {
        var anonymous = api.CreateClient();
        var forged = api.CreateClient();
        forged.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue(
            "Bearer",
            LocalTokens.Issue("a-different-signing-key-that-is-long-enough", ReviewAuthentication.DefaultAudience, "mallory", DateTime.UtcNow.AddMinutes(5)));

        Assert.Equal(HttpStatusCode.Unauthorized, (await anonymous.GetAsync("/api/workspaces")).StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, (await forged.GetAsync("/api/workspaces")).StatusCode);
    }

    [Fact]
    public async Task Creator_becomes_the_owner()
    {
        var owner = api.ClientFor("ada");

        var created = await owner.PostJsonAsync("/api/workspaces", new { name = "  Airway review  " });
        var workspace = await created.ReadAsync<WorkspaceResponse>();
        var listed = await (await owner.GetAsync("/api/workspaces")).ReadAsync<List<WorkspaceResponse>>();

        Assert.Equal(HttpStatusCode.Created, created.StatusCode);
        Assert.Equal("Airway review", workspace.Name);
        Assert.Equal(WorkspaceRole.Owner, workspace.Role);
        Assert.Contains(listed, w => w.Id == workspace.Id && w.Role == WorkspaceRole.Owner);
    }

    [Fact]
    public async Task Blank_workspace_names_are_rejected()
    {
        var response = await api.ClientFor("ada").PostJsonAsync("/api/workspaces", new { name = "   " });

        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task Only_members_can_read_and_only_owners_can_change_membership()
    {
        var owner = api.ClientFor("grace");
        var workspace = await (await owner.PostJsonAsync("/api/workspaces", new { name = "Methods" })).ReadAsync<WorkspaceResponse>();
        var members = $"/api/workspaces/{workspace.Id}/members";
        var reviewer = api.ClientFor("linus");
        var outsider = api.ClientFor("eve");

        Assert.Equal(HttpStatusCode.Forbidden, (await outsider.GetAsync(members)).StatusCode);
        Assert.Equal(HttpStatusCode.OK, (await owner.PutJsonAsync(members, new { subject = "linus", role = "reviewer" })).StatusCode);

        var listed = await (await reviewer.GetAsync(members)).ReadAsync<List<MemberResponse>>();
        Assert.Equal(["grace", "linus"], listed.Select(m => m.Subject));
        Assert.Equal(HttpStatusCode.Forbidden, (await reviewer.PutJsonAsync(members, new { subject = "eve", role = "viewer" })).StatusCode);
        Assert.Equal(HttpStatusCode.Forbidden, (await outsider.PutJsonAsync(members, new { subject = "eve", role = "owner" })).StatusCode);
    }

    [Fact]
    public async Task The_last_owner_cannot_be_demoted()
    {
        var owner = api.ClientFor("barbara");
        var workspace = await (await owner.PostJsonAsync("/api/workspaces", new { name = "Ownership" })).ReadAsync<WorkspaceResponse>();
        var members = $"/api/workspaces/{workspace.Id}/members";

        var demoted = await owner.PutJsonAsync(members, new { subject = "barbara", role = "editor" });
        await owner.PutJsonAsync(members, new { subject = "ken", role = "owner" });
        var demotedWithSecondOwner = await owner.PutJsonAsync(members, new { subject = "barbara", role = "editor" });

        Assert.Equal(HttpStatusCode.Conflict, demoted.StatusCode);
        Assert.Equal(HttpStatusCode.OK, demotedWithSecondOwner.StatusCode);
        Assert.Equal(WorkspaceRole.Editor, (await demotedWithSecondOwner.ReadAsync<MemberResponse>()).Role);
    }
}
