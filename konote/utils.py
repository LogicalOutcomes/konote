"""Shared utility functions used across multiple apps."""
from django.shortcuts import redirect


def get_client_ip(request):
    """Get client IP address, respecting X-Forwarded-For from reverse proxy."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def is_embed_request(request):
    """Check if request is in embed mode (?embed=1)."""
    return request.GET.get("embed") == "1"


def redirect_preserving_embed(request, url_name, **kwargs):
    """Redirect while preserving ?embed=1 if present."""
    resp = redirect(url_name, **kwargs)
    if is_embed_request(request):
        sep = "&" if "?" in resp["Location"] else "?"
        resp["Location"] += f"{sep}embed=1"
    return resp
