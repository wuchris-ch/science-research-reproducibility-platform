using Azure;
using Azure.Storage.Blobs;
using Azure.Storage.Blobs.Models;

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

    // IfNoneMatch "*" makes the upload fail instead of overwriting an existing blob.
    public async Task UploadAsync(string blobName, Stream content, string contentType, string sha256, CancellationToken cancellationToken) =>
        await container.GetBlobClient(blobName).UploadAsync(
            content,
            new BlobUploadOptions
            {
                HttpHeaders = new BlobHttpHeaders { ContentType = contentType },
                Metadata = new Dictionary<string, string> { ["sha256"] = sha256 },
                Conditions = new BlobRequestConditions { IfNoneMatch = ETag.All },
            },
            cancellationToken);

    public async Task<Stream> OpenReadAsync(string blobName, CancellationToken cancellationToken) =>
        await container.GetBlobClient(blobName).OpenReadAsync(cancellationToken: cancellationToken);

    // Cleanup runs even when the request was cancelled.
    public async Task DeleteAsync(string blobName) =>
        await container.GetBlobClient(blobName).DeleteIfExistsAsync(DeleteSnapshotsOption.IncludeSnapshots, cancellationToken: CancellationToken.None);
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
