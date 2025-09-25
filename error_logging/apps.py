from django.apps import AppConfig


class ErrorLoggingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "error_logging"
    verbose_name = "System Error Logging"
