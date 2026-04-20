from django.contrib import admin
from .models import CandidateProfile, RecruiterFeedback


@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    list_display = ["id", "candidate_name", "total_experience_years", "is_shortlisted", "created_at"]
    list_filter = ["is_shortlisted"]
    search_fields = ["resume__filename"]
    readonly_fields = ["structured_profile", "embedding_vector", "profile_text", "bias_flags"]


@admin.register(RecruiterFeedback)
class RecruiterFeedbackAdmin(admin.ModelAdmin):
    list_display = ["candidate", "job", "action", "created_at"]
    list_filter = ["action"]
