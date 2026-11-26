from django.apps import AppConfig


class PredictionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "prediction"

    def ready(self):
        import prediction.signals  # noqa: F401
