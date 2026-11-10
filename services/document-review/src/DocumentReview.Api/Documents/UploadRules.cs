using Microsoft.Net.Http.Headers;

namespace DocumentReview.Api.Documents;

public sealed class DocumentOptions
{
    public long MaxUploadBytes { get; set; } = 25 * 1024 * 1024;
}

public sealed record UploadProblem(string Field, string Message);

public static class UploadRules
{
    public const int MaxTitleLength = 300;
    public const int MaxNoteLength = 2000;
    public const int MaxFileNameLength = 255;
    public const string DefaultContentType = "application/octet-stream";

    public static UploadProblem? Validate(string? fileName, long length, string? note, long maxBytes)
    {
        if (length <= 0)
        {
            return new UploadProblem("file", "Upload a non-empty file.");
        }

        if (length > maxBytes)
        {
            return new UploadProblem("file", $"Files must be at most {maxBytes} bytes.");
        }

        if (SafeFileName(fileName) is null)
        {
            return new UploadProblem("file", $"File names must be 1 to {MaxFileNameLength} characters without control characters.");
        }

        return note?.Length > MaxNoteLength ? new UploadProblem("note", $"Notes must be at most {MaxNoteLength} characters.") : null;
    }

    public static UploadProblem? ValidateTitle(string? title) =>
        string.IsNullOrWhiteSpace(title) || title.Trim().Length > MaxTitleLength
            ? new UploadProblem("title", $"Title must be 1 to {MaxTitleLength} characters.")
            : null;

    // Keeps only the last path segment so a client cannot supply a path, and rejects control characters.
    public static string? SafeFileName(string? fileName)
    {
        var name = fileName?.Replace('\\', '/').Split('/')[^1].Trim();
        return string.IsNullOrEmpty(name) || name.Length > MaxFileNameLength || name.Any(char.IsControl) ? null : name;
    }

    public static string ContentType(string? declared) =>
        MediaTypeHeaderValue.TryParse(declared, out var parsed) && parsed.MediaType.Value is { Length: <= 200 } mediaType
            ? mediaType
            : DefaultContentType;

    public static string BlobName(Guid workspaceId, Guid documentId, Guid revisionId) =>
        $"{workspaceId:N}/{documentId:N}/{revisionId:N}";
}
