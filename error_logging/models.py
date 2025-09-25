import logging
import traceback
from typing import Optional

from django.conf import settings
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class ErrorLog(models.Model):
    """Database representation of captured application errors."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="error_logs",
    )
    status_code = models.PositiveIntegerField()
    module = models.CharField(max_length=255, blank=True)
    path = models.CharField(max_length=500, blank=True)
    method = models.CharField(max_length=16, blank=True)
    message = models.TextField()
    stack_trace = models.TextField(blank=True)
    resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_error_logs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("status_code", "resolved")),
            models.Index(fields=("resolved", "created_at")),
        ]

    def __str__(self) -> str:  # pragma: no cover - convenience string formatting
        timestamp = timezone.localtime(self.created_at).strftime("%Y-%m-%d %H:%M:%S")
        return f"[{self.status_code}] {self.module or self.path} @ {timestamp}"

    @classmethod
    def record(
        cls,
        *,
        request,
        message: str,
        status_code: int,
        exception: Optional[BaseException] = None,
    ) -> None:
        """Persist an error that occurred while handling ``request``.

        Args:
            request: The Django ``HttpRequest`` instance being processed.
            message: Short description of the error.
            status_code: HTTP status associated with the error.
            exception: Optional original exception for stack trace capture.
        """

        user = getattr(request, "user", None)
        if not getattr(user, "is_authenticated", False):
            user = None

        resolver_match = getattr(request, "resolver_match", None)
        module = ""
        if resolver_match is not None:
            module = resolver_match.view_name or getattr(
                resolver_match.func, "__qualname__", ""
            )

        path = getattr(request, "path", "")[:500]
        method = getattr(request, "method", "")[:16]

        stack_trace = ""
        if exception is not None:
            stack_trace = "".join(
                traceback.format_exception(
                    exception.__class__, exception, exception.__traceback__
                )
            )

        try:
            cls.objects.create(
                user=user,
                status_code=status_code,
                module=module or path,
                path=path,
                method=method,
                message=str(message),
                stack_trace=stack_trace,
            )
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Failed to persist error log entry")

    def mark_resolved(self, *, user=None) -> None:
        """Mark the error as resolved and persist the change."""

        self.resolved = True
        self.resolved_at = timezone.now()
        if user is not None and getattr(user, "is_authenticated", False):
            self.resolved_by = user
        self.save(update_fields=["resolved", "resolved_at", "resolved_by", "updated_at"])

    def mark_unresolved(self) -> None:
        """Reset the resolved state for the log entry."""

        self.resolved = False
        self.resolved_at = None
        self.resolved_by = None
        self.save(update_fields=["resolved", "resolved_at", "resolved_by", "updated_at"])
