using System.Net.Http.Headers;
using System.Text.Json;
using System.Text.Json.Serialization;
using Azure.Storage.Blobs;
using DocumentReview.Api.Auth;
using DocumentReview.Api.Data;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Data.SqlClient;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;

namespace DocumentReview.Tests;

// Runs the real API against SQL Server and Azurite. Each test class gets its own database and blob container,
// which the fixture deletes afterwards.
public sealed class ReviewApiFactory : WebApplicationFactory<Program>, IAsyncLifetime
{
    public const string SigningKey = "test-only-signing-key-for-document-review-0123456789";

    public static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web)
    {
        Converters = { new JsonStringEnumConverter(JsonNamingPolicy.CamelCase) },
    };

    public static string SqlServer =>
        Environment.GetEnvironmentVariable("DOCUMENT_REVIEW_TEST_SQL")
        ?? "Server=localhost,1433;User Id=sa;Password=Review_Local_2026!;TrustServerCertificate=True";

    public static string BlobStorage =>
        Environment.GetEnvironmentVariable("DOCUMENT_REVIEW_TEST_BLOBS") ?? "UseDevelopmentStorage=true";

    public string DatabaseName { get; } = $"DocumentReviewTest_{Guid.NewGuid():N}";

    public string ContainerName { get; } = $"test-{Guid.NewGuid():N}";

    public BlobContainerClient Container => new(BlobStorage, ContainerName);

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        var database = new SqlConnectionStringBuilder(SqlServer) { InitialCatalog = DatabaseName };
        builder.UseEnvironment("Testing");
        builder.UseSetting("ConnectionStrings:ReviewDatabase", database.ConnectionString);
        builder.UseSetting("BlobStorage:ConnectionString", BlobStorage);
        builder.UseSetting("BlobStorage:Container", ContainerName);
        builder.UseSetting("Auth:LocalSigningKey", SigningKey);
        builder.UseSetting("InitializeStorageOnStartup", "true");
    }

    public HttpClient ClientFor(string subject)
    {
        var client = CreateClient();
        client.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue(
            "Bearer", LocalTokens.Issue(SigningKey, ReviewAuthentication.DefaultAudience, subject, DateTime.UtcNow.AddMinutes(10)));
        return client;
    }

    public async Task<T> WithDatabaseAsync<T>(Func<ReviewDbContext, Task<T>> query)
    {
        using var scope = Services.CreateScope();
        return await query(scope.ServiceProvider.GetRequiredService<ReviewDbContext>());
    }

    public Task InitializeAsync()
    {
        // Starting the server applies the migrations and creates the blob container.
        _ = Server;
        return Task.CompletedTask;
    }

    async Task IAsyncLifetime.DisposeAsync()
    {
        await WithDatabaseAsync(db => db.Database.EnsureDeletedAsync());
        await Container.DeleteIfExistsAsync();
        await DisposeAsync();
    }
}
