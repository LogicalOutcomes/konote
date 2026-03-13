"""Serve the standalone config generator HTML from the admin UI."""
from pathlib import Path

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

from apps.auth_app.decorators import admin_required

CONFIG_GENERATOR_PATH = Path(__file__).resolve().parent.parent.parent / "tools" / "config-generator.html"


@login_required
@admin_required
def config_generator(request):
    """Serve the config generator HTML file directly."""
    html = CONFIG_GENERATOR_PATH.read_text(encoding="utf-8")
    nonce = str(getattr(request, "csp_nonce", ""))
    if nonce:
        html = html.replace("<script>", f'<script nonce="{nonce}">', 1)
    return HttpResponse(html)
