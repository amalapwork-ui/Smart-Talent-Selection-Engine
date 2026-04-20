import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ResumesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "resumes"

    def ready(self):
        # Pre-load the sentence-transformers model in a background thread so the
        # first resume parse doesn't pay the 2-5s cold-start cost.
        import threading

        def _warm():
            try:
                from ai_pipeline.embeddings import get_embedding_model
                get_embedding_model()
                logger.info("Embedding model pre-warmed at startup.")
            except Exception as e:
                logger.warning("Embedding model pre-warm failed (non-fatal): %s", e)

        threading.Thread(target=_warm, daemon=True).start()
