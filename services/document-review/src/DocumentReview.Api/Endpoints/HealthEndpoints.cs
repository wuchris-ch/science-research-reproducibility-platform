using DocumentReview.Api.Data;
using DocumentReview.Api.Storage;

namespace DocumentReview.Api.Endpoints;

public static class HealthEndpoints
{
    public static void MapHealthEndpoints(this IEndpointRouteBuilder app) =>
        app.MapGet("/healthz", CheckAsync).AllowAnonymous();

    static async Task<IResult> CheckAsync(ReviewDbContext db, DocumentBlobStore blobs, CancellationToken cancellationToken)
    {
        var database = await db.Database.CanConnectAsync(cancellationToken);
        var blobStorage = await blobs.IsAvailableAsync(cancellationToken);
        var body = new { database = database ? "ok" : "unavailable", blobStorage = blobStorage ? "ok" : "unavailable" };
        return database && blobStorage ? Results.Ok(body) : Results.Json(body, statusCode: StatusCodes.Status503ServiceUnavailable);
    }
}
