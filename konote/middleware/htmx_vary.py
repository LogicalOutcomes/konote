"""Middleware to add Vary: HX-Request header to all responses.

Multiple views return different templates based on the HX-Request header
(HTMX partial vs full page). Without this Vary header, browser caches
cannot distinguish the two response types for the same URL, causing
broken pages when the user navigates back via the browser Back button.
"""
from django.utils.cache import patch_vary_headers


class HtmxVaryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        patch_vary_headers(response, ["HX-Request"])
        return response
