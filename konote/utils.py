"""Shared utility functions used across multiple apps."""


def get_client_ip(request):
    """Get client IP address, respecting X-Forwarded-For from reverse proxy."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
