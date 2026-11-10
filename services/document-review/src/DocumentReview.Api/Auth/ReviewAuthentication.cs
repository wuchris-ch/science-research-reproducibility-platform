using System.Security.Claims;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Authorization;
using Microsoft.IdentityModel.Tokens;

namespace DocumentReview.Api.Auth;

public static class ReviewAuthentication
{
    public const string SubjectClaim = "sub";
    public const string DefaultAudience = "document-review";

    public static IServiceCollection AddReviewAuthentication(this IServiceCollection services)
    {
        services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme).AddJwtBearer();
        services.AddOptions<JwtBearerOptions>(JwtBearerDefaults.AuthenticationScheme)
            .Configure<IConfiguration>(Configure);
        services.AddAuthorizationBuilder()
            .SetFallbackPolicy(new AuthorizationPolicyBuilder()
                .RequireAuthenticatedUser()
                .RequireAssertion(context => context.User.FindFirstValue(SubjectClaim) is { Length: >= 1 and <= 200 })
                .Build());
        return services;
    }

    public static string Subject(this ClaimsPrincipal user) => user.FindFirstValue(SubjectClaim)!;

    // Team installations use an OIDC issuer (RS256 through its discovery document), the same model as the
    // workbench API. Local development and tests use a symmetric key. Exactly one of the two must be configured.
    static void Configure(JwtBearerOptions options, IConfiguration configuration)
    {
        var auth = configuration.GetSection("Auth");
        var authority = auth["Authority"];
        var audience = auth["Audience"] ?? DefaultAudience;
        var localKey = auth["LocalSigningKey"];
        options.MapInboundClaims = false;

        if (!string.IsNullOrEmpty(authority) && !string.IsNullOrEmpty(localKey))
        {
            throw new InvalidOperationException("Configure either Auth:Authority or Auth:LocalSigningKey, not both.");
        }

        if (!string.IsNullOrEmpty(authority))
        {
            options.Authority = authority;
            options.Audience = audience;
            options.TokenValidationParameters.ValidAlgorithms = [SecurityAlgorithms.RsaSha256];
        }
        else if (!string.IsNullOrEmpty(localKey))
        {
            options.TokenValidationParameters = new TokenValidationParameters
            {
                ValidIssuer = LocalTokens.Issuer,
                ValidAudience = audience,
                IssuerSigningKey = LocalTokens.SigningKey(localKey),
                ValidAlgorithms = [SecurityAlgorithms.HmacSha256],
                RequireExpirationTime = true,
            };
        }
        else
        {
            throw new InvalidOperationException("Configure Auth:Authority for OIDC or Auth:LocalSigningKey for local development.");
        }

        options.TokenValidationParameters.NameClaimType = SubjectClaim;
    }
}
