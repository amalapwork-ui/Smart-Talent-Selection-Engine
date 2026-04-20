from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RankingResultViewSet, RankingRunViewSet

router = DefaultRouter()
router.register(r"results", RankingResultViewSet, basename="ranking-result")
router.register(r"runs", RankingRunViewSet, basename="ranking-run")

urlpatterns = [path("", include(router.urls))]
