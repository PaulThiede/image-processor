# app/middleware/rate_limiter.py

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time, hashlib

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_calls: int = 5, period: int = 60):
        super().__init__(app)
        self.max_calls = max_calls
        self.period = period
        self.usage: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next):
        # Get IP
        ip = request.client.host or "unknown"
        uid = hashlib.sha256(ip.encode()).hexdigest()

        now = time.time()
        timestamps = self.usage.setdefault(uid, [])
        # Remove old entries
        timestamps[:] = [t for t in timestamps if now - t < self.period]

        if len(timestamps) >= self.max_calls:
            retry_after = self.period - (now - timestamps[0])
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded. Retry after {retry_after:.1f} seconds"},
                headers={"Retry-After": str(int(retry_after))}
            )

        timestamps.append(now)
        return await call_next(request)
