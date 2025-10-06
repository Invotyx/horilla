from django.contrib import admin

from .models import ErrorLog


@admin.register(ErrorLog)
class ErrorLogAdmin(admin.ModelAdmin):
    list_display = (
        "status_code",
        "module",
        "path",
        "user",
        "resolved",
        "resolved_at",
        "created_at",
    )
    list_filter = ("status_code", "resolved", "module", "user")
    search_fields = ("module", "path", "message", "stack_trace")
    readonly_fields = (
        "user",
        "status_code",
        "module",
        "path",
        "method",
        "message",
        "stack_trace",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)
