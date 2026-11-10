using System.Text;
using Microsoft.IdentityModel.JsonWebTokens;
using Microsoft.IdentityModel.Tokens;

namespace DocumentReview.Api.Auth;

public static class LocalTokens
{
    public const string Issuer = "document-review-local";

    public static SymmetricSecurityKey SigningKey(string secret)
    {
        var bytes = Encoding.UTF8.GetBytes(secret);
        if (bytes.Length < 32)
        {
            throw new InvalidOperationException("Auth:LocalSigningKey must be at least 32 bytes.");
        }

        return new SymmetricSecurityKey(bytes);
    }

    public static string Issue(IConfiguration configuration, string subject, TimeSpan lifetime)
    {
        var secret = configuration["Auth:LocalSigningKey"]
            ?? throw new InvalidOperationException("Auth:LocalSigningKey is not configured.");
        var audience = configuration["Auth:Audience"] ?? ReviewAuthentication.DefaultAudience;
        return Issue(secret, audience, subject, DateTime.UtcNow.Add(lifetime));
    }

    public static string Issue(string secret, string audience, string subject, DateTime expires) =>
        new JsonWebTokenHandler().CreateToken(new SecurityTokenDescriptor
        {
            Issuer = Issuer,
            Audience = audience,
            Claims = new Dictionary<string, object> { [ReviewAuthentication.SubjectClaim] = subject },
            Expires = expires,
            SigningCredentials = new SigningCredentials(SigningKey(secret), SecurityAlgorithms.HmacSha256),
        });
}
