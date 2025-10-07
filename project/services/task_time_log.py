"""Utilities to manage task based time logging bound to timesheets."""

from __future__ import annotations

from collections import OrderedDict
from typing import Dict, Optional, Tuple

from django.db import transaction
from django.utils import timezone

from project.models import Project, TaskTimeLog, TimeSheet, seconds_to_duration


def _duration_to_seconds(value: Optional[str]) -> int:
    """Convert a HH:MM string into seconds."""

    if not value:
        return 0
    try:
        hours, minutes = value.split(":")
        return int(hours) * 3600 + int(minutes) * 60
    except (ValueError, TypeError):
        return 0


def _today():
    return timezone.localdate()


def _collect_today_timesheets(employee) -> Dict[Tuple[int, str], TimeSheet]:
    """Return a mapping of (project_id, task_name) to today's timesheet entry."""

    timesheets = TimeSheet.objects.filter(
        employee_id=employee,
        date=_today(),
    )
    mapping: Dict[Tuple[int, str], TimeSheet] = {}
    for sheet in timesheets:
        key = (sheet.project_id_id, sheet.task_name)
        mapping.setdefault(key, sheet)
    return mapping


def get_employee_task_options(employee) -> Dict[str, object]:
    """Build grouped task data for the dropdown."""

    today = _today()
    logs = list(
        TaskTimeLog.objects.filter(employee=employee, date=today)
        .select_related("project")
        .order_by("project__title", "task_name")
    )
    log_map: Dict[Tuple[int, str], TaskTimeLog] = {
        (log.project_id, log.task_name): log for log in logs
    }
    active_log = next((log for log in logs if log.active), None)

    qs = (
        TimeSheet.objects.filter(employee_id=employee)
        .filter(status__in=["in_Progress", "completed"])
        .exclude(project_id__isnull=True)
        .exclude(task_name__isnull=True)
        .exclude(task_name__exact="")
        .values("project_id", "project_id__title", "task_name")
        .distinct()
    )

    combos: Dict[Tuple[int, str], str] = OrderedDict()
    for entry in qs:
        project_id = entry["project_id"]
        task_name = entry["task_name"]
        if project_id is None or not task_name:
            continue
        combos[(project_id, task_name)] = entry["project_id__title"]

    # Ensure active logs are visible even if timesheet entry was archived
    for log in logs:
        combos.setdefault((log.project_id, log.task_name), log.project.title)

    today_timesheets = _collect_today_timesheets(employee)
    now = timezone.now()

    grouped: Dict[int, Dict[str, object]] = OrderedDict()
    for (project_id, task_name), project_name in sorted(
        combos.items(), key=lambda item: (item[1].lower(), item[0][1].lower())
    ):
        group = grouped.setdefault(
            project_id,
            {
                "id": project_id,
                "name": project_name,
                "tasks": [],
            },
        )
        log = log_map.get((project_id, task_name))
        seconds = 0
        if log:
            seconds = log.total_seconds
            if log.active and log.started_at:
                seconds += max(int((now - log.started_at).total_seconds()), 0)
        else:
            sheet = today_timesheets.get((project_id, task_name))
            if sheet:
                seconds = _duration_to_seconds(sheet.time_spent)

        task_info = {
            "project_id": project_id,
            "task_name": task_name,
            "label": f"{project_name}: {task_name}",
            "active": bool(log and log.active),
            "time_display": seconds_to_duration(seconds),
        }
        group["tasks"].append(task_info)

    active_payload = None
    if active_log:
        active_project_name = combos.get(
            (active_log.project_id, active_log.task_name), active_log.project.title
        )
        active_seconds = active_log.total_seconds
        if active_log.started_at:
            active_seconds += max(int((now - active_log.started_at).total_seconds()), 0)
        active_payload = {
            "project_id": active_log.project_id,
            "task_name": active_log.task_name,
            "label": f"{active_project_name}: {active_log.task_name}",
            "time_display": seconds_to_duration(active_seconds),
        }

    return {
        "projects": list(grouped.values()),
        "active": active_payload,
    }


@transaction.atomic
def stop_active_log(employee, *, mark_complete: bool = False) -> Optional[TaskTimeLog]:
    """Stop any active timer for the employee."""

    log = (
        TaskTimeLog.objects.select_for_update()
        .filter(employee=employee, active=True)
        .first()
    )
    if not log:
        return None
    log.stop(mark_complete=mark_complete)
    return log


@transaction.atomic
def toggle_task_log(employee, project_id: int, task_name: str) -> Dict[str, object]:
    """Start or stop tracking for the provided task."""

    today = _today()
    now = timezone.now()
    active_log = (
        TaskTimeLog.objects.select_for_update()
        .filter(employee=employee, active=True)
        .first()
    )

    if active_log:
        same_task = (
            active_log.project_id == project_id
            and active_log.task_name == task_name
            and active_log.date == today
        )
        active_log.stop()
        if same_task:
            return {"status": "stopped", "active": None, "stopped": active_log}

    project = Project.objects.get(id=project_id)
    # Ensure the task exists in the employee timesheets
    if not TimeSheet.objects.filter(
        employee_id=employee,
        project_id=project,
        task_name=task_name,
    ).exists():
        raise ValueError("Task not available for this employee")

    log, created = TaskTimeLog.objects.select_for_update().get_or_create(
        employee=employee,
        project=project,
        task_name=task_name,
        date=today,
        defaults={"active": True, "started_at": now},
    )
    if not created:
        log.started_at = now
        log.active = True
        log.save(update_fields=["started_at", "active"])
    return {"status": "started", "active": log}
