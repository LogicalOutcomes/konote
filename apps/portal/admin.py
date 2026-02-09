"""Django admin registration for participant portal models."""
from django.contrib import admin

from .models import CorrectionRequest, ParticipantUser, PortalInvite


@admin.register(ParticipantUser)
class ParticipantUserAdmin(admin.ModelAdmin):
    """Admin view for participant portal accounts.

    Note: The ``email`` property decrypts on access, so it cannot be used
    in list_display directly. We show the display_name and client_file
    instead. The email_hash is shown for debugging lookup issues.
    """

    list_display = [
        "display_name",
        "client_file",
        "is_active",
        "mfa_method",
        "preferred_language",
        "created_at",
    ]
    list_filter = ["is_active", "mfa_method", "preferred_language"]
    search_fields = ["display_name"]
    readonly_fields = [
        "id",
        "email_hash",
        "failed_login_count",
        "locked_until",
        "created_at",
        "last_login",
    ]
    # Exclude encrypted binary fields from the form
    exclude = ["_email_encrypted", "_totp_secret_encrypted", "password"]


@admin.register(PortalInvite)
class PortalInviteAdmin(admin.ModelAdmin):
    """Admin view for portal invites."""

    list_display = [
        "client_file",
        "invited_by",
        "status",
        "consent_document_version",
        "created_at",
        "expires_at",
    ]
    list_filter = ["status", "consent_document_version"]
    search_fields = ["token"]
    readonly_fields = ["token", "created_at", "accepted_at"]


@admin.register(CorrectionRequest)
class CorrectionRequestAdmin(admin.ModelAdmin):
    """Admin view for participant correction requests."""

    list_display = [
        "participant_user",
        "client_file",
        "data_type",
        "status",
        "created_at",
        "resolved_at",
    ]
    list_filter = ["status", "data_type"]
    readonly_fields = ["created_at", "resolved_at"]
    # Exclude encrypted binary field from the form
    exclude = ["_description_encrypted"]
