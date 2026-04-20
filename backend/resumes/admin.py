from django.contrib import admin
from .models import Resume


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ["filename", "job_role", "status", "parse_confidence", "upload_date"]
    list_filter = ["status", "job_role", "file_type"]
    search_fields = ["filename", "job_role"]
    readonly_fields = ["raw_text", "parsed_sections", "content_hash", "parse_confidence"]
