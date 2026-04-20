from django.contrib import admin
from .models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ["title", "department", "is_active", "min_experience_years", "created_at"]
    list_filter = ["is_active", "employment_type"]
    search_fields = ["title", "description", "department"]
