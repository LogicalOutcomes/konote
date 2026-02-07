"""Public registration views."""
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.clients.models import CustomFieldDefinition

from .forms import PublicRegistrationForm
from .models import RegistrationLink, RegistrationSubmission
from .utils import approve_submission


def _is_embed_mode(request):
    """Check if request is for embed mode (iframe display)."""
    return request.GET.get("embed") == "1"


def _render_with_frame_options(request, template, context, allow_framing=False):
    """Render template with appropriate X-Frame-Options header.

    Args:
        request: The HTTP request
        template: Template path to render
        context: Template context dict
        allow_framing: If True, allows the page to be embedded in iframes

    Returns:
        HttpResponse, optionally exempt from X-Frame-Options
    """
    response = render(request, template, context)
    if allow_framing:
        # Tell Django's XFrameOptionsMiddleware to skip this response,
        # allowing the page to be embedded in iframes on other domains.
        response.xframe_options_exempt = True
    return response


# Rate limiting constants
MAX_SUBMISSIONS_PER_HOUR = 5
RATE_LIMIT_SESSION_KEY = "registration_submissions"


def _check_rate_limit(request):
    """Check if the session has exceeded the submission rate limit.

    Returns:
        tuple: (is_limited, remaining_submissions)
    """
    now = timezone.now()
    submissions = request.session.get(RATE_LIMIT_SESSION_KEY, [])

    # Filter to only submissions in the last hour
    one_hour_ago = now - timezone.timedelta(hours=1)
    recent_submissions = [
        ts for ts in submissions
        if timezone.datetime.fromisoformat(ts) > one_hour_ago
    ]

    # Update session with filtered list
    request.session[RATE_LIMIT_SESSION_KEY] = recent_submissions

    remaining = MAX_SUBMISSIONS_PER_HOUR - len(recent_submissions)
    is_limited = remaining <= 0

    return is_limited, max(0, remaining)


def _record_submission(request):
    """Record a submission timestamp in the session for rate limiting."""
    submissions = request.session.get(RATE_LIMIT_SESSION_KEY, [])
    submissions.append(timezone.now().isoformat())
    request.session[RATE_LIMIT_SESSION_KEY] = submissions


def _get_capacity_info(registration_link):
    """Get capacity information for display.

    Returns:
        dict with 'remaining', 'total', 'has_limit' keys
    """
    if not registration_link.max_registrations:
        return {"remaining": None, "total": None, "has_limit": False}

    # Count pending and approved submissions
    used = registration_link.submissions.filter(
        status__in=["pending", "approved"]
    ).count()
    remaining = registration_link.max_registrations - used

    return {
        "remaining": max(0, remaining),
        "total": registration_link.max_registrations,
        "has_limit": True,
    }


def _get_grouped_custom_fields(registration_link):
    """Get custom fields organized by group for template display.

    Returns:
        list of dicts with 'group' and 'fields' keys
    """
    field_groups = registration_link.field_groups.filter(status="active").order_by("sort_order")
    grouped = []

    for group in field_groups:
        fields = CustomFieldDefinition.objects.filter(
            group=group,
            status="active",
        ).order_by("sort_order")

        if fields.exists():
            grouped.append({
                "group": group,
                "fields": list(fields),
            })

    return grouped


@require_http_methods(["GET", "POST"])
def public_registration_form(request, slug):
    """Display the public registration form for a registration link.

    GET: Show the registration form
    POST: Validate and create a submission

    Supports embed mode with ?embed=1 query parameter for iframe embedding.
    In embed mode:
    - Uses minimal template (no header/footer)
    - Allows framing (X-Frame-Options: ALLOWALL)
    - Form targets parent window on submit
    """
    # Check for embed mode (iframe display)
    embed_mode = _is_embed_mode(request)

    # Look up the registration link
    try:
        registration_link = RegistrationLink.objects.select_related("program").get(
            slug=slug
        )
    except RegistrationLink.DoesNotExist:
        raise Http404("Registration form not found.")

    # Check if registration is open - use model's is_closed_reason property
    closed_reason = registration_link.is_closed_reason
    is_open = closed_reason is None

    # Select template based on mode
    form_template = "registration/public_form_embed.html" if embed_mode else "registration/public_form.html"
    closed_template = "registration/closed_embed.html" if embed_mode else "registration/closed.html"

    # If closed, show the closed page with appropriate message
    if closed_reason:
        return _render_with_frame_options(
            request,
            closed_template,
            {"registration_link": registration_link, "reason": closed_reason},
            allow_framing=embed_mode,
        )

    # Get capacity info for display
    capacity = _get_capacity_info(registration_link)

    # Get grouped custom fields for display
    grouped_fields = _get_grouped_custom_fields(registration_link)

    # Check rate limit
    is_rate_limited, remaining_submissions = _check_rate_limit(request)

    context = {
        "registration_link": registration_link,
        "is_open": is_open,
        "capacity": capacity,
        "grouped_fields": grouped_fields,
        "is_rate_limited": is_rate_limited,
        "remaining_submissions": remaining_submissions,
        "spots_remaining": registration_link.spots_remaining,
        "embed_mode": embed_mode,
    }

    if request.method == "GET":
        if is_open and not is_rate_limited:
            form = PublicRegistrationForm(registration_link=registration_link)
            context["form"] = form
        return _render_with_frame_options(request, form_template, context, allow_framing=embed_mode)

    # POST handling - re-check if still open (race condition protection)
    closed_reason = registration_link.is_closed_reason
    if closed_reason:
        return _render_with_frame_options(
            request,
            closed_template,
            {"registration_link": registration_link, "reason": closed_reason},
            allow_framing=embed_mode,
        )

    if is_rate_limited:
        context["rate_limit_error"] = True
        return _render_with_frame_options(request, form_template, context, allow_framing=embed_mode)

    form = PublicRegistrationForm(request.POST, registration_link=registration_link)
    context["form"] = form

    if not form.is_valid():
        return _render_with_frame_options(request, form_template, context, allow_framing=embed_mode)

    # Create the submission
    submission = RegistrationSubmission(
        registration_link=registration_link,
    )

    # Set encrypted PII fields
    submission.first_name = form.cleaned_data["first_name"]
    submission.last_name = form.cleaned_data["last_name"]
    submission.email = form.cleaned_data["email"]
    submission.phone = form.cleaned_data.get("phone", "")

    # Store custom field values
    submission.field_values = form.get_custom_field_values()

    # Save the submission first
    submission.save()

    # Handle auto-approve if enabled - this creates ClientFile and enrolment
    if registration_link.auto_approve:
        approve_submission(submission, reviewed_by=None)

    # Record submission for rate limiting
    _record_submission(request)

    # Store reference number in session for the confirmation page
    request.session["last_submission_ref"] = submission.reference_number
    request.session["last_submission_auto_approved"] = registration_link.auto_approve

    # Redirect - preserve embed mode
    redirect_url = f"/register/{slug}/submitted/"
    if embed_mode:
        redirect_url += "?embed=1"
    return redirect(redirect_url)


def registration_submitted(request, slug):
    """Display confirmation after a registration is submitted.

    Supports embed mode with ?embed=1 for iframe display.
    """
    embed_mode = _is_embed_mode(request)

    # Look up the registration link (for branding/context)
    try:
        registration_link = RegistrationLink.objects.select_related("program").get(
            slug=slug
        )
    except RegistrationLink.DoesNotExist:
        raise Http404("Registration form not found.")

    # Get submission info from session
    reference_number = request.session.pop("last_submission_ref", None)
    auto_approved = request.session.pop("last_submission_auto_approved", False)

    # If no reference number in session, try query param (for bookmarking)
    if not reference_number:
        reference_number = request.GET.get("ref")

    context = {
        "registration_link": registration_link,
        "reference_number": reference_number,
        "auto_approved": auto_approved,
        "embed_mode": embed_mode,
    }

    template = "registration/submitted_embed.html" if embed_mode else "registration/submitted.html"
    return _render_with_frame_options(request, template, context, allow_framing=embed_mode)
