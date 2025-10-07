"""API views that back the task based attendance timer."""

from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods

from project.models import Project
from project.services import task_time_log as service


def _get_employee(request):
    return getattr(request.user, "employee_get", None)


def _serialize_log(log):
    return service.serialize_log(log)


@login_required
@require_http_methods(["GET"])
def task_time_log_options(request):
    employee = _get_employee(request)
    if not employee:
        return JsonResponse({"projects": [], "active": None})

    payload = service.get_employee_task_options(employee)
    return JsonResponse(payload)


@login_required
@require_http_methods(["POST"])
def task_time_log_toggle(request):
    employee = _get_employee(request)
    if not employee:
        return JsonResponse({"error": _("Employee profile not found.")}, status=400)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        payload = request.POST

    project_id = payload.get("project_id")
    task_name = payload.get("task_name")
    if not project_id or not task_name:
        return JsonResponse({"error": _("Project and task are required.")}, status=400)

    try:
        project_identifier = int(project_id)
    except (TypeError, ValueError):
        return JsonResponse({"error": _("Invalid project reference.")}, status=400)

    try:
        result = service.toggle_task_log(employee, project_identifier, str(task_name))
    except Project.DoesNotExist:
        return JsonResponse({"error": _("Project not found.")}, status=404)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)

    active = result.get("active")
    response = {
        "status": result.get("status"),
        "active": _serialize_log(active),
    }
    return JsonResponse(response)


@login_required
@require_http_methods(["POST"])
def task_time_log_stop(request):
    employee = _get_employee(request)
    if not employee:
        return JsonResponse({"status": "idle"})

    mark_complete = request.GET.get("complete") in {"1", "true", "True"}
    log = service.stop_active_log(employee, mark_complete=mark_complete)
    if not log:
        return JsonResponse({"status": "idle"})
    return JsonResponse({"status": "stopped", "log": _serialize_log(log)})
