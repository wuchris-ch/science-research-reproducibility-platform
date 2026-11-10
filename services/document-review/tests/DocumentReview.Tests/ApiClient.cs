using System.Net.Http.Headers;
using System.Net.Http.Json;
using DocumentReview.Api.Endpoints;

namespace DocumentReview.Tests;

static class ApiClient
{
    public static async Task<T> ReadAsync<T>(this HttpResponseMessage response) =>
        (await response.Content.ReadFromJsonAsync<T>(ReviewApiFactory.Json))!;

    public static Task<HttpResponseMessage> PostJsonAsync(this HttpClient client, string path, object body) =>
        client.PostAsJsonAsync(path, body, ReviewApiFactory.Json);

    public static Task<HttpResponseMessage> PutJsonAsync(this HttpClient client, string path, object body) =>
        client.PutAsJsonAsync(path, body, ReviewApiFactory.Json);

    public static MultipartFormDataContent Upload(string fileName, byte[] bytes, string contentType = "application/pdf", params (string Name, string Value)[] fields)
    {
        var form = new MultipartFormDataContent();
        var file = new ByteArrayContent(bytes);
        file.Headers.ContentType = MediaTypeHeaderValue.Parse(contentType);
        form.Add(file, "file", fileName);
        foreach (var (name, value) in fields)
        {
            form.Add(new StringContent(value), name);
        }

        return form;
    }

    public static async Task<WorkspaceResponse> CreateWorkspaceAsync(this HttpClient owner, params (string Subject, string Role)[] members)
    {
        var workspace = await (await owner.PostJsonAsync("/api/workspaces", new { name = "Review workspace" })).ReadAsync<WorkspaceResponse>();
        foreach (var (subject, role) in members)
        {
            (await owner.PutJsonAsync($"/api/workspaces/{workspace.Id}/members", new { subject, role })).EnsureSuccessStatusCode();
        }

        return workspace;
    }

    public static async Task<DocumentResponse> CreateDocumentAsync(this HttpClient editor, Guid workspaceId, byte[] bytes, string title = "Methods appendix")
    {
        var response = await editor.PostAsync(
            $"/api/workspaces/{workspaceId}/documents", Upload("methods.pdf", bytes, fields: ("title", title)));
        response.EnsureSuccessStatusCode();
        return await response.ReadAsync<DocumentResponse>();
    }
}
