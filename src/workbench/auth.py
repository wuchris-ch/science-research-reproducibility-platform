import secrets
import time
from urllib.parse import urlsplit

import jwt
from fastapi import Request

from .service import Problem


class Auth:
    def __init__(self, settings):
        self.settings = settings
        key = settings.data_dir / "session.key"
        if not key.exists():
            try:
                with key.open("x") as f:
                    f.write(secrets.token_hex(32))
                key.chmod(0o600)
            except FileExistsError:
                pass
        self.key = key.read_text().strip()
        if any((settings.oidc_issuer, settings.oidc_audience, settings.oidc_jwks_url)) and not all(
            (settings.oidc_issuer, settings.oidc_audience, settings.oidc_jwks_url)
        ):
            raise RuntimeError("OIDC requires issuer, audience and JWKS URL together")
        if settings.oidc_issuer and not settings.oidc_jwks_url.startswith("https://"):
            raise RuntimeError("OIDC JWKS must use HTTPS")
        self.jwks = jwt.PyJWKClient(settings.oidc_jwks_url) if settings.oidc_issuer else None

    def check_origin(self, request):
        origin = request.headers.get("origin")
        if origin and origin not in self.settings.origins:
            raise Problem(403, "Origin denied")
        if request.headers.get("sec-fetch-site") == "cross-site":
            raise Problem(403, "Cross-site request denied")
        if request.headers.get("host") not in {urlsplit(o).netloc for o in self.settings.origins}:
            raise Problem(403, "Host denied")

    def session(self, request):
        self.check_origin(request)
        if self.jwks:
            raise Problem(401, "Use an OIDC access token for this installation")
        existing = request.cookies.get("research_session", "")
        try:
            claims = jwt.decode(
                existing,
                self.key,
                algorithms=["HS256"],
                audience="research-local",
                options={"require": ["exp", "sub", "csrf"]},
            )
            return existing, claims["csrf"]
        except jwt.PyJWTError:
            pass
        csrf = secrets.token_urlsafe(32)
        token = jwt.encode(
            {"sub": "local", "csrf": csrf, "exp": int(time.time()) + 86400, "aud": "research-local"},
            self.key,
            algorithm="HS256",
        )
        return token, csrf

    def actor(self, request: Request):
        self.check_origin(request)
        bearer = request.headers.get("authorization", "")
        if self.jwks:
            if not bearer.startswith("Bearer "):
                raise Problem(401, "OIDC access token required")
            token = bearer[7:]
            try:
                key = self.jwks.get_signing_key_from_jwt(token)
                claims = jwt.decode(
                    token,
                    key.key,
                    algorithms=["RS256"],
                    audience=self.settings.oidc_audience,
                    issuer=self.settings.oidc_issuer,
                    options={"require": ["exp", "iat", "sub"]},
                )
            except Exception:
                raise Problem(401, "Invalid identity token") from None
        else:
            try:
                claims = jwt.decode(
                    request.cookies.get("research_session", ""),
                    self.key,
                    algorithms=["HS256"],
                    audience="research-local",
                    options={"require": ["exp", "sub", "csrf"]},
                )
            except jwt.PyJWTError:
                raise Problem(401, "Start a local session") from None
            if request.method not in ("GET", "HEAD", "OPTIONS") and not secrets.compare_digest(
                request.headers.get("x-csrf-token", ""), claims["csrf"]
            ):
                raise Problem(403, "CSRF token required")
        subject = claims.get("sub")
        if not isinstance(subject, str) or not 1 <= len(subject) <= 200:
            raise Problem(401, "Invalid subject")
        return subject
