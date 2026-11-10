using DocumentReview.Api.Documents;

namespace DocumentReview.Tests;

public class UploadRulesTests
{
    [Fact]
    public void Accepts_a_named_non_empty_file_within_the_limit() =>
        Assert.Null(UploadRules.Validate("methods.pdf", 100, "First draft", 1000));

    [Theory]
    [InlineData("methods.pdf", 0, null, "file")]
    [InlineData("methods.pdf", 1001, null, "file")]
    [InlineData("", 10, null, "file")]
    [InlineData("bad\u0007name.pdf", 10, null, "file")]
    public void Rejects_invalid_files(string fileName, long length, string? note, string field) =>
        Assert.Equal(field, UploadRules.Validate(fileName, length, note, 1000)?.Field);

    [Fact]
    public void Rejects_long_notes() =>
        Assert.Equal("note", UploadRules.Validate("methods.pdf", 10, new string('x', UploadRules.MaxNoteLength + 1), 1000)?.Field);

    [Theory]
    [InlineData(null)]
    [InlineData("   ")]
    public void Requires_a_title(string? title) =>
        Assert.Equal("title", UploadRules.ValidateTitle(title)?.Field);

    [Theory]
    [InlineData("../../etc/passwd", "passwd")]
    [InlineData("C:\\Users\\ada\\report.docx", "report.docx")]
    [InlineData("  notes.txt ", "notes.txt")]
    [InlineData("folder/", null)]
    public void File_names_keep_only_the_last_path_segment(string fileName, string? expected) =>
        Assert.Equal(expected, UploadRules.SafeFileName(fileName));

    [Theory]
    [InlineData("application/pdf", "application/pdf")]
    [InlineData("text/plain; charset=utf-8", "text/plain")]
    [InlineData("not a media type", "application/octet-stream")]
    [InlineData(null, "application/octet-stream")]
    public void Content_types_fall_back_to_octet_stream(string? declared, string expected) =>
        Assert.Equal(expected, UploadRules.ContentType(declared));

    [Fact]
    public void Blob_names_are_unique_per_revision_and_grouped_by_document()
    {
        var workspace = Guid.Parse("11111111-1111-1111-1111-111111111111");
        var document = Guid.Parse("22222222-2222-2222-2222-222222222222");
        var revision = Guid.Parse("33333333-3333-3333-3333-333333333333");

        Assert.Equal(
            "11111111111111111111111111111111/22222222222222222222222222222222/33333333333333333333333333333333",
            UploadRules.BlobName(workspace, document, revision));
    }
}
