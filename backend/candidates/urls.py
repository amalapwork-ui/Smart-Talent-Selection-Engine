from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CandidateProfileViewSet

router = DefaultRouter()
router.register(r"", CandidateProfileViewSet, basename="candidate")

urlpatterns = [path("", include(router.urls))]
