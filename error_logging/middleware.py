import logging

from django.http import Http404

from .models import ErrorLog

logger = logging.getLogger(__name__)


class ErrorLoggingMiddleware:
    """Persist unhandled exceptions and error responses for diagnostics."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = None
        try:
            response = self.get_response(request)
        except Exception as exc:  # pragma: no cover - defensive branch
            self._log_exception(request, exc)
            raise

        if response is not None:
            self._log_response(request, response)
        return response

    def process_exception(self, request, exception):  # pragma: no cover - Django hook
        self._log_exception(request, exception)
        request._error_log_recorded = True
        return None

    def _log_exception(self, request, exception: BaseException) -> None:
        status_code = getattr(exception, "status_code", 500)
        if isinstance(exception, Http404):
            status_code = 404
        try:
            ErrorLog.record(
                request=request,
                message=str(exception),
                status_code=status_code,
                exception=exception,
            )
            request._error_log_recorded = True
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Unable to capture exception details for error logging")

    def _log_response(self, request, response) -> None:
        status_code = getattr(response, "status_code", None)
        if status_code not in {404, 500}:
            return
        if getattr(request, "_error_log_recorded", False):
            return
        message = getattr(response, "reason_phrase", "") or f"HTTP {status_code}"
        try:
            ErrorLog.record(
                request=request,
                message=message,
                status_code=status_code,
                exception=None,
            )
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Unable to capture response details for error logging")
