from django.contrib import admin

from apps.programs.models import UserProgramRole

from .models import (
    ClientAccessBlock,
    ClientDetailValue,
    ClientFile,
    ClientProgramEnrolment,
    CustomFieldDefinition,
    CustomFieldGroup,
)


def _get_accessible_client_ids(user):
    """Return set of client IDs the user can access based on program roles.

    Security: Superuser/admin status does NOT grant automatic access.
    User must have an active UserProgramRole for each program.
    Filters by current enrolments only (status="enrolled").
    """
    user_program_ids = set(
        UserProgramRole.objects.filter(user=user, status="active")
        .values_list("program_id", flat=True)
    )
    if not user_program_ids:
        return set()
    return set(
        ClientProgramEnrolment.objects.filter(
            program_id__in=user_program_ids, status="enrolled",
        ).values_list("client_file_id", flat=True)
    )


def _get_accessible_program_ids(user):
    """Return set of program IDs the user has active roles in."""
    return set(
        UserProgramRole.objects.filter(user=user, status="active")
        .values_list("program_id", flat=True)
    )


class ConfidentialClientAdminMixin:
    """Mixin that enforces confidential program boundaries in Django admin.

    Filters list views via get_queryset() AND blocks direct URL access
    via object-level permission checks (has_view/change/delete_permission).

    Security: Superuser status does NOT bypass these checks.
    """

    def _user_can_access_client(self, user, client_id):
        """Check if user has program access to a specific client."""
        accessible_ids = _get_accessible_client_ids(user)
        return client_id in accessible_ids

    def has_view_permission(self, request, obj=None):
        if obj is not None:
            return self._user_can_access_client(request.user, obj.pk)
        return super().has_view_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            return self._user_can_access_client(request.user, obj.pk)
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None:
            return self._user_can_access_client(request.user, obj.pk)
        return super().has_delete_permission(request, obj)


@admin.register(ClientFile)
class ClientFileAdmin(ConfidentialClientAdminMixin, admin.ModelAdmin):
    # Encrypted PII fields excluded — use property accessors in readonly
    list_display = ("id", "record_id", "status", "is_demo", "created_at")
    list_filter = ("status", "is_demo")
    search_fields = ("record_id",)
    readonly_fields = ("is_demo",)  # Security: is_demo set at creation only

    def get_queryset(self, request):
        """Filter to clients the user can access via program roles.

        Security: Superusers do NOT automatically see confidential clients.
        They need explicit UserProgramRole for each confidential program.
        Preserves demo/real separation (enforced by is_demo list_filter).
        """
        qs = super().get_queryset(request)
        accessible_ids = _get_accessible_client_ids(request.user)
        if not accessible_ids:
            return qs.none()
        return qs.filter(pk__in=accessible_ids)


@admin.register(ClientProgramEnrolment)
class ClientProgramEnrolmentAdmin(admin.ModelAdmin):
    list_display = ("client_file", "program", "enrolled_at", "status")
    list_filter = ("status",)

    def get_queryset(self, request):
        """Filter enrolments by both client AND program access.

        Security: Prevents discovering confidential program names
        through the enrolment list.
        """
        qs = super().get_queryset(request)
        accessible_program_ids = _get_accessible_program_ids(request.user)
        if not accessible_program_ids:
            return qs.none()
        return qs.filter(program_id__in=accessible_program_ids)

    def has_view_permission(self, request, obj=None):
        if obj is not None:
            program_ids = _get_accessible_program_ids(request.user)
            return obj.program_id in program_ids
        return super().has_view_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            program_ids = _get_accessible_program_ids(request.user)
            return obj.program_id in program_ids
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None:
            program_ids = _get_accessible_program_ids(request.user)
            return obj.program_id in program_ids
        return super().has_delete_permission(request, obj)


@admin.register(ClientAccessBlock)
class ClientAccessBlockAdmin(admin.ModelAdmin):
    list_display = ("user", "client_file", "reason", "created_by", "created_at", "is_active")
    list_filter = ("is_active",)
    raw_id_fields = ("user", "client_file", "created_by")


@admin.register(CustomFieldGroup)
class CustomFieldGroupAdmin(admin.ModelAdmin):
    list_display = ("title", "sort_order")


@admin.register(CustomFieldDefinition)
class CustomFieldDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "input_type", "group", "is_required", "is_sensitive")
    list_filter = ("input_type", "is_required", "is_sensitive")


@admin.register(ClientDetailValue)
class ClientDetailValueAdmin(ConfidentialClientAdminMixin, admin.ModelAdmin):
    list_display = ("client_file", "field_def", "id")

    def _user_can_access_client(self, user, obj_pk):
        """For ClientDetailValue, check access via the parent client."""
        try:
            obj = ClientDetailValue.objects.get(pk=obj_pk)
            accessible_ids = _get_accessible_client_ids(user)
            return obj.client_file_id in accessible_ids
        except ClientDetailValue.DoesNotExist:
            return False

    def get_queryset(self, request):
        """Filter custom field values to only show accessible clients."""
        qs = super().get_queryset(request)
        accessible_ids = _get_accessible_client_ids(request.user)
        if not accessible_ids:
            return qs.none()
        return qs.filter(client_file_id__in=accessible_ids)
