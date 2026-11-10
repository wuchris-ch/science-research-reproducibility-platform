namespace DocumentReview.Api.Endpoints;

static class Problems
{
    public static IResult AccessDenied() => Results.Problem(statusCode: StatusCodes.Status403Forbidden, title: "Workspace access denied");

    public static IResult Conflict(string title) => Results.Problem(statusCode: StatusCodes.Status409Conflict, title: title);

    public static IResult NotFound(string title) => Results.Problem(statusCode: StatusCodes.Status404NotFound, title: title);

    public static IResult Invalid(string field, string message) =>
        Results.ValidationProblem(new Dictionary<string, string[]> { [field] = [message] });
}
