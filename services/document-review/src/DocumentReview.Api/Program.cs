using System.Text.Json;
using System.Text.Json.Serialization;
using DocumentReview.Api.Access;
using DocumentReview.Api.Auth;
using DocumentReview.Api.Data;
using DocumentReview.Api.Documents;
using DocumentReview.Api.Endpoints;
using DocumentReview.Api.Storage;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);

if (args is ["issue-token", var tokenSubject])
{
    // Prints a short-lived token signed with Auth:LocalSigningKey for local development.
    Console.WriteLine(LocalTokens.Issue(builder.Configuration, tokenSubject, TimeSpan.FromHours(8)));
    return;
}

builder.Services.AddOpenApi();
builder.Services.AddProblemDetails();
builder.Services.ConfigureHttpJsonOptions(options =>
    options.SerializerOptions.Converters.Add(new JsonStringEnumConverter(JsonNamingPolicy.CamelCase)));
builder.Services.AddSingleton(TimeProvider.System);
builder.Services.AddDbContext<ReviewDbContext>((services, options) =>
    options.UseSqlServer(services.GetRequiredService<IConfiguration>().GetConnectionString("ReviewDatabase")));
builder.Services.AddScoped<WorkspaceAccess>();
builder.Services.AddScoped<RevisionStore>();
builder.Services.AddOptions<DocumentOptions>().BindConfiguration("Documents");
builder.Services.AddDocumentBlobStore();
builder.Services.AddReviewAuthentication();

var app = builder.Build();

if (app.Configuration.GetValue<bool>("InitializeStorageOnStartup"))
{
    using var scope = app.Services.CreateScope();
    await scope.ServiceProvider.GetRequiredService<ReviewDbContext>().Database.MigrateAsync();
    await scope.ServiceProvider.GetRequiredService<DocumentBlobStore>().InitializeAsync(CancellationToken.None);
}

app.UseExceptionHandler();
app.UseStatusCodePages();
app.UseAuthentication();
app.UseAuthorization();

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi().AllowAnonymous();
}

app.MapHealthEndpoints();
app.MapWorkspaceEndpoints();
app.MapDocumentEndpoints();
app.MapReviewEndpoints();

await app.RunAsync();

public partial class Program;
