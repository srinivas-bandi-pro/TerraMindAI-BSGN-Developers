"""A small in-memory fixed-window rate limiter for API requests."""

from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from flask import Flask, jsonify, request


class BasicRateLimiter:
    """Limit API requests per client IP without requiring external services."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: defaultdict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def is_allowed(self, client_key: str) -> bool:
        """Return whether a client may make another request in this window."""
        now = monotonic()

        with self._lock:
            request_times = self._requests[client_key]
            while request_times and now - request_times[0] >= self.window_seconds:
                request_times.popleft()

            if len(request_times) >= self.limit:
                return False

            request_times.append(now)
            return True


def configure_rate_limiter(app: Flask) -> None:
    """Register basic API-only rate limiting on the Flask application."""
    limiter = BasicRateLimiter(
        app.config["RATE_LIMIT_REQUESTS"],
        app.config["RATE_LIMIT_WINDOW_SECONDS"],
    )
    app.extensions["rate_limiter"] = limiter

    @app.before_request
    def limit_api_requests():
        """Reject excessive requests with a JSON-safe response."""
        if not request.path.startswith("/api/"):
            return None

        client_key = request.remote_addr or "unknown"
        if limiter.is_allowed(client_key):
            return None

        app.logger.warning("Rate limit exceeded for client %s.", client_key)
        response = jsonify(
            {
                "success": False,
                "error": {
                    "code": "rate_limit_exceeded",
                    "message": "Too many requests. Please try again later.",
                },
            }
        )
        response.headers["Retry-After"] = str(app.config["RATE_LIMIT_WINDOW_SECONDS"])
        return response, 429
