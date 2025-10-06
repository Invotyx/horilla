from django.urls import path

from . import views

app_name = "error_logging"

urlpatterns = [
    path("error-logs/", views.error_log_list, name="error-log-list"),
    path("error-logs/bulk/", views.bulk_update_error_logs, name="error-log-bulk"),
    path(
        "error-logs/<int:pk>/toggle/",
        views.toggle_error_resolution,
        name="error-log-toggle",
    ),
]
