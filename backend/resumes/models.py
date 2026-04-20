import os
from django.db import models


def resume_upload_path(instance, filename):
    return f"resumes/{instance.job_role}/{filename}"


class Resume(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("done", "Done"),
        ("error", "Error"),
    ]

    file = models.FileField(upload_to=resume_upload_path)
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20)
    job_role = models.CharField(max_length=200, blank=True, default="General")
    batch_date = models.DateField(auto_now_add=True)
    upload_date = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    parse_confidence = models.FloatField(default=0.0)
    raw_text = models.TextField(blank=True)
    parsed_sections = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    # Duplicate detection hash
    content_hash = models.CharField(max_length=64, blank=True, db_index=True)

    class Meta:
        ordering = ["-upload_date"]

    def __str__(self):
        return f"{self.filename} ({self.status})"

    @property
    def file_size_kb(self):
        try:
            return round(self.file.size / 1024, 1)
        except Exception:
            return 0
