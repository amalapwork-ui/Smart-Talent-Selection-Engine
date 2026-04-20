from django.db import models


class Job(models.Model):
    title = models.CharField(max_length=300)
    description = models.TextField()
    required_skills = models.JSONField(default=list)
    preferred_skills = models.JSONField(default=list)
    min_experience_years = models.PositiveIntegerField(default=0)
    education_required = models.CharField(max_length=200, blank=True)
    department = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=200, blank=True)
    employment_type = models.CharField(
        max_length=50,
        choices=[
            ("full_time", "Full Time"),
            ("part_time", "Part Time"),
            ("contract", "Contract"),
            ("internship", "Internship"),
        ],
        default="full_time",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Parsed JD requirements (from AI)
    parsed_requirements = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({'Active' if self.is_active else 'Closed'})"

    @property
    def candidate_count(self):
        return self.rankingresult_set.values("candidate__resume__job_role").distinct().count()
