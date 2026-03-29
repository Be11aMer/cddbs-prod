"""Security headers middleware for the CDDBS API.

Adds standard security headers to all API responses:
- X-Content-Type-Options: Prevent MIME-type sniffing
- X-Frame-Options: Prevent clickjacking
- Referrer-Policy: Limit referrer leakage
- Permissions-Policy: Disable unused browser features
- Content-Security-Policy: API-only CSP
- Cache-Control: Prevent caching of API responses
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        response.headers["Cache-Control"] = "no-store"
        return response
