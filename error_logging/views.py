import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from .models import ErrorLog

logger = logging.getLogger(__name__)


@login_required
@permission_required("error_logging.view_errorlog", raise_exception=True)
def error_log_list(request: HttpRequest) -> HttpResponse:
    """Render an overview of captured error logs with filtering support."""

    logs = ErrorLog.objects.select_related("user", "resolved_by")

    status_code = request.GET.get("status")
    if status_code:
        try:
            logs = logs.filter(status_code=int(status_code))
        except (TypeError, ValueError):
            messages.warning(request, _("Status code must be a number."))

    resolved_filter = request.GET.get("resolved")
    if resolved_filter == "resolved":
        logs = logs.filter(resolved=True)
    elif resolved_filter == "unresolved":
        logs = logs.filter(resolved=False)

    user_filter = request.GET.get("user")
    if user_filter:
        logs = logs.filter(user_id=user_filter)

    module_filter = request.GET.get("module")
    if module_filter:
        logs = logs.filter(module__icontains=module_filter)

    search_query = request.GET.get("q")
    if search_query:
        logs = logs.filter(
            Q(message__icontains=search_query)
            | Q(stack_trace__icontains=search_query)
            | Q(path__icontains=search_query)
        )

    logs = logs.order_by("-created_at")

    paginator = Paginator(logs, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    user_model = get_user_model()
    users = (
        user_model.objects.filter(error_logs__isnull=False)
        .order_by("username")
        .distinct()
    )

    query_params = request.GET.copy()
    query_params.pop("page", None)

    context = {
        "page_obj": page_obj,
        "logs": page_obj.object_list,
        "status_codes": list(
            ErrorLog.objects.order_by("status_code")
            .values_list("status_code", flat=True)
            .distinct()
        ),
        "users": users,
        "filter_values": {
            "status": status_code or "",
            "resolved": resolved_filter or "",
            "user": user_filter or "",
            "module": module_filter or "",
            "q": search_query or "",
        },
        "summary": {
            "total": ErrorLog.objects.count(),
            "resolved": ErrorLog.objects.filter(resolved=True).count(),
            "unresolved": ErrorLog.objects.filter(resolved=False).count(),
        },
        "querystring": query_params.urlencode(),
    }
    return render(request, "error_logging/error_log_list.html", context)


@login_required
@permission_required("error_logging.change_errorlog", raise_exception=True)
@require_POST
def toggle_error_resolution(request: HttpRequest, pk: int) -> HttpResponse:
    """Toggle an error log between resolved and unresolved states."""

    log_entry = get_object_or_404(ErrorLog, pk=pk)
    action = request.POST.get("action", "toggle")

    if action == "resolve":
        if not log_entry.resolved:
            log_entry.mark_resolved(user=request.user)
            messages.success(request, _("Error marked as resolved."))
        else:
            messages.info(request, _("Error is already resolved."))
    elif action == "unresolve":
        if log_entry.resolved:
            log_entry.mark_unresolved()
            messages.success(request, _("Error marked as unresolved."))
        else:
            messages.info(request, _("Error is already unresolved."))
    else:
        if log_entry.resolved:
            log_entry.mark_unresolved()
            messages.success(request, _("Error marked as unresolved."))
        else:
            log_entry.mark_resolved(user=request.user)
            messages.success(request, _("Error marked as resolved."))

    return redirect(
        request.META.get(
            "HTTP_REFERER", reverse("error_logging:error-log-list")
        )
    )


def page_not_found(request: HttpRequest, exception) -> HttpResponse:
    """Custom 404 handler that ensures the error is captured in the log."""

    if not getattr(request, "_error_log_recorded", False):
        try:
            ErrorLog.record(
                request=request,
                message=str(exception),
                status_code=404,
                exception=exception,
            )
            request._error_log_recorded = True
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Failed to record 404 error log entry")
    return render(request, "decorator_404.html", status=404)


def server_error(request: HttpRequest) -> HttpResponse:
    """Custom 500 handler that ensures the error is captured in the log."""

    if not getattr(request, "_error_log_recorded", False):
        try:
            ErrorLog.record(
                request=request,
                message="Internal Server Error",
                status_code=500,
            )
            request._error_log_recorded = True
        except Exception:  # pragma: no cover - defensive logging
            logger.exception("Failed to record 500 error log entry")
    return render(request, "went_wrong.html", status=500)
