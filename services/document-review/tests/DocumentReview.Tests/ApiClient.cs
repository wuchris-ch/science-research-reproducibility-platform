using System.Net.Http.Json;

namespace DocumentReview.Tests;

static class ApiClient
{
    public static async Task<T> ReadAsync<T>(this HttpResponseMessage response) =>
        (await response.Content.ReadFromJsonAsync<T>(ReviewApiFactory.Json))!;

    public static Task<HttpResponseMessage> PostJsonAsync(this HttpClient client, string path, object body) =>
        client.PostAsJsonAsync(path, body, ReviewApiFactory.Json);

    public static Task<HttpResponseMessage> PutJsonAsync(this HttpClient client, string path, object body) =>
        client.PutAsJsonAsync(path, body, ReviewApiFactory.Json);
}
