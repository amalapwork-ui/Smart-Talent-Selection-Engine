"""
pytest configuration — sets Django settings and disables Celery eager execution
so tasks can be mocked without actually running.
"""
import django
from django.conf import settings


def pytest_configure(config):
    settings.CELERY_TASK_ALWAYS_EAGER = False
    settings.CELERY_TASK_EAGER_PROPAGATES = False
