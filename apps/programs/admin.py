from django.contrib import admin

from .models import Program, UserProgramRole


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "is_confidential", "created_at")
    list_filter = ("status", "is_confidential")
    search_fields = ("name",)

    def get_readonly_fields(self, request, obj=None):
        # One-way rule: once confidential, can't revert without formal PIA
        if obj and obj.is_confidential:
            return ("is_confidential",)
        return ()


@admin.register(UserProgramRole)
class UserProgramRoleAdmin(admin.ModelAdmin):
    list_display = ("user", "program", "role")
    list_filter = ("role",)
