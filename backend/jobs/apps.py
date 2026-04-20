import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class JobsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "jobs"

    def ready(self):
        from django.conf import settings
        key = getattr(settings, "GROQ_API_KEY", "")
        if key:
            logger.info("GROQ_API_KEY loaded: YES (AI features enabled)")
        else:
            logger.warning(
                "GROQ_API_KEY loaded: NO — add GROQ_API_KEY to backend/.env "
                "to enable AI-powered JD suggestions and justifications"
            )
