using Azure;
using Azure.Storage.Blobs;

namespace DocumentReview.Api.Storage;

// File bytes live in Azure Blob Storage. SQL Server keeps only metadata and the blob name.
public sealed class DocumentBlobStore(BlobContainerClient container)
{
    public async Task InitializeAsync(CancellationToken cancellationToken) =>
        await container.CreateIfNotExistsAsync(cancellationToken: cancellationToken);

    public async Task<bool> IsAvailableAsync(CancellationToken cancellationToken)
    {
        try
        {
            return (await container.ExistsAsync(cancellationToken)).Value;
        }
        catch (RequestFailedException)
        {
            return false;
        }
    }
}

public static class DocumentBlobStoreRegistration
{
    public static IServiceCollection AddDocumentBlobStore(this IServiceCollection services) =>
        services.AddSingleton(provider =>
        {
            var configuration = provider.GetRequiredService<IConfiguration>();
            var connectionString = configuration["BlobStorage:ConnectionString"]
                ?? throw new InvalidOperationException("BlobStorage:ConnectionString is not configured.");
            var containerName = configuration["BlobStorage:Container"] ?? "document-revisions";
            return new DocumentBlobStore(new BlobContainerClient(connectionString, containerName));
        });
}
