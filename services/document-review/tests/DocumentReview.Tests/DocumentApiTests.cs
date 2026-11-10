using System.Net;
using System.Security.Cryptography;
using System.Text;
using Azure.Storage.Blobs.Models;
using DocumentReview.Api.Endpoints;
using Microsoft.EntityFrameworkCore;

namespace DocumentReview.Tests;

public class DocumentApiTests(ReviewApiFactory api) : IClassFixture<ReviewApiFactory>
{
    static byte[] Bytes(string text) => Encoding.UTF8.GetBytes(text);

    static string Sha256(byte[] bytes) => Convert.ToHexStringLower(SHA256.HashData(bytes));

    [Fact]
    public async Task Upload_stores_bytes_in_blob_storage_and_metadata_in_sql_server()
    {
        var owner = api.ClientFor("ada");
        var workspace = await owner.CreateWorkspaceAsync();
        var bytes = Bytes("%PDF-1.7 methods appendix, first draft");

        var document = await owner.CreateDocumentAsync(workspace.Id, bytes);
        var row = await api.WithDatabaseAsync(db => db.DocumentRevisions.SingleAsync(r => r.DocumentId == document.Id));
        var blob = api.Container.GetBlobClient(row.BlobName);
        var stored = (await blob.DownloadContentAsync()).Value;

        Assert.Equal(1, document.LatestRevision.Number);
        Assert.Equal(Sha256(bytes), document.LatestRevision.Sha256);
        Assert.Equal(bytes.Length, row.SizeBytes);
        Assert.Equal(bytes, stored.Content.ToArray());
        Assert.Equal("application/pdf", stored.Details.ContentType);
        Assert.Equal(Sha256(bytes), stored.Details.Metadata["sha256"]);
    }

    [Fact]
    public async Task Each_upload_adds_a_revision_and_every_revision_stays_downloadable()
    {
        var owner = api.ClientFor("grace");
        var workspace = await owner.CreateWorkspaceAsync();
        var document = await owner.CreateDocumentAsync(workspace.Id, Bytes("draft one"));

        var second = await owner.PostAsync(
            $"/api/documents/{document.Id}/revisions",
            ApiClient.Upload("methods-v2.txt", Bytes("draft two"), "text/plain", ("note", "Adds the filter threshold")));
        var revisions = await (await owner.GetAsync($"/api/documents/{document.Id}/revisions")).ReadAsync<List<RevisionResponse>>();
        var first = await owner.GetAsync($"/api/documents/{document.Id}/revisions/1/content");
        var latest = await owner.GetAsync($"/api/documents/{document.Id}/revisions/2/content");

        Assert.Equal(HttpStatusCode.Created, second.StatusCode);
        Assert.Equal([1, 2], revisions.Select(r => r.Number));
        Assert.Equal("Adds the filter threshold", revisions[1].Note);
        Assert.Equal("draft one", await first.Content.ReadAsStringAsync());
        Assert.Equal("draft two", await latest.Content.ReadAsStringAsync());
        Assert.Equal("text/plain", latest.Content.Headers.ContentType?.MediaType);
        Assert.Equal("methods-v2.txt", latest.Content.Headers.ContentDisposition?.FileNameStar);
        Assert.Equal(HttpStatusCode.NotFound, (await owner.GetAsync($"/api/documents/{document.Id}/revisions/3/content")).StatusCode);
    }

    [Fact]
    public async Task A_stale_expected_revision_is_refused_and_its_blob_is_removed()
    {
        var owner = api.ClientFor("barbara");
        var workspace = await owner.CreateWorkspaceAsync();
        var document = await owner.CreateDocumentAsync(workspace.Id, Bytes("one"));
        var path = $"/api/documents/{document.Id}/revisions";

        var current = await owner.PostAsync(path, ApiClient.Upload("two.pdf", Bytes("two"), fields: ("expectedLatestRevision", "1")));
        var stale = await owner.PostAsync(path, ApiClient.Upload("other.pdf", Bytes("other"), fields: ("expectedLatestRevision", "1")));
        var prefix = $"{workspace.Id:N}/{document.Id:N}/";
        var blobs = new List<string>();
        await foreach (var item in api.Container.GetBlobsAsync(new GetBlobsOptions { Prefix = prefix }))
        {
            blobs.Add(item.Name);
        }

        Assert.Equal(HttpStatusCode.Created, current.StatusCode);
        Assert.Equal(HttpStatusCode.Conflict, stale.StatusCode);
        Assert.Equal(2, blobs.Count);
    }

    [Fact]
    public async Task Concurrent_uploads_receive_consecutive_revision_numbers()
    {
        var owner = api.ClientFor("ken");
        var workspace = await owner.CreateWorkspaceAsync();
        var document = await owner.CreateDocumentAsync(workspace.Id, Bytes("base"));

        var responses = await Task.WhenAll(Enumerable.Range(0, 6).Select(i =>
            owner.PostAsync($"/api/documents/{document.Id}/revisions", ApiClient.Upload($"draft-{i}.pdf", Bytes($"draft {i}")))));
        var numbers = await Task.WhenAll(responses.Select(async r => (await r.ReadAsync<RevisionResponse>()).Number));

        Assert.All(responses, r => Assert.Equal(HttpStatusCode.Created, r.StatusCode));
        Assert.Equal([2, 3, 4, 5, 6, 7], numbers.Order());
    }

    [Fact]
    public async Task Roles_control_upload_and_reading()
    {
        var owner = api.ClientFor("linus");
        var workspace = await owner.CreateWorkspaceAsync(("vint", "viewer"), ("radia", "reviewer"), ("dennis", "editor"));
        var document = await owner.CreateDocumentAsync(workspace.Id, Bytes("draft"));
        var revisions = $"/api/documents/{document.Id}/revisions";
        var viewer = api.ClientFor("vint");
        var outsider = api.ClientFor("eve");

        Assert.Equal(HttpStatusCode.OK, (await viewer.GetAsync($"{revisions}/1/content")).StatusCode);
        Assert.Equal(HttpStatusCode.Forbidden, (await viewer.PostAsync(revisions, ApiClient.Upload("v.pdf", Bytes("v")))).StatusCode);
        Assert.Equal(HttpStatusCode.Forbidden, (await api.ClientFor("radia").PostAsync(revisions, ApiClient.Upload("r.pdf", Bytes("r")))).StatusCode);
        Assert.Equal(HttpStatusCode.Created, (await api.ClientFor("dennis").PostAsync(revisions, ApiClient.Upload("e.pdf", Bytes("e")))).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await outsider.GetAsync(revisions)).StatusCode);
        Assert.Equal(HttpStatusCode.NotFound, (await outsider.GetAsync($"{revisions}/1/content")).StatusCode);
        Assert.Equal(HttpStatusCode.Forbidden, (await outsider.GetAsync($"/api/workspaces/{workspace.Id}/documents")).StatusCode);
    }

    [Fact]
    public async Task Invalid_uploads_are_rejected_before_storage()
    {
        var owner = api.ClientFor("frances");
        var workspace = await owner.CreateWorkspaceAsync();
        var documents = $"/api/workspaces/{workspace.Id}/documents";

        var empty = await owner.PostAsync(documents, ApiClient.Upload("empty.pdf", [], fields: ("title", "Empty")));
        var tooLarge = await owner.PostAsync(
            documents, ApiClient.Upload("large.pdf", new byte[ReviewApiFactory.MaxUploadBytes + 1], fields: ("title", "Large")));
        var untitled = await owner.PostAsync(documents, ApiClient.Upload("draft.pdf", Bytes("draft")));
        var pathName = await owner.PostAsync(documents, ApiClient.Upload("../../secrets/plan.pdf", Bytes("plan"), fields: ("title", "Plan")));

        Assert.Equal(HttpStatusCode.BadRequest, empty.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, tooLarge.StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, untitled.StatusCode);
        Assert.Equal("plan.pdf", (await pathName.ReadAsync<DocumentResponse>()).LatestRevision.FileName);
        Assert.Single(await (await owner.GetAsync(documents)).ReadAsync<List<DocumentResponse>>());
    }
}
