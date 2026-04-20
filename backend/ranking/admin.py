from django.contrib import admin
from .models import RankingResult, RankingRun


@admin.register(RankingResult)
class RankingResultAdmin(admin.ModelAdmin):
    list_display = ["job", "candidate", "total_score", "rank_position", "created_at"]
    list_filter = ["job"]
    ordering = ["-total_score"]
    readonly_fields = ["score_breakdown", "justification"]


@admin.register(RankingRun)
class RankingRunAdmin(admin.ModelAdmin):
    list_display = ["job", "status", "total_candidates", "processed_candidates", "started_at"]
    list_filter = ["status"]
