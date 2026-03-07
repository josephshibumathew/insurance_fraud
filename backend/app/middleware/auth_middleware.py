"""Authentication middleware for request context hydration."""

from __future__ import annotations

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.security import decode_token


class AuthMiddleware(BaseHTTPMiddleware):
    PUBLIC_PREFIXES = {
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
    }

    async def dispatch(self, request: Request, call_next: Callable):
        request.state.user = None

        path = request.url.path
        if any(path.startswith(prefix) for prefix in self.PUBLIC_PREFIXES):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1]
            try:
                payload = decode_token(token)
                request.state.user = {"id": payload.get("sub"), "role": payload.get("role")}
            except Exception:
                request.state.user = None

        return await call_next(request)
