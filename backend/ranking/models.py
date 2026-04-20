from django.db import models


class RankingResult(models.Model):
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE)
    candidate = models.ForeignKey("candidates.CandidateProfile", on_delete=models.CASCADE)

    total_score = models.FloatField(default=0.0)
    skill_score = models.FloatField(default=0.0)
    experience_score = models.FloatField(default=0.0)
    project_score = models.FloatField(default=0.0)
    education_score = models.FloatField(default=0.0)

    score_breakdown = models.JSONField(default=dict)
    justification = models.TextField(blank=True)
    rank_position = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("job", "candidate")
        ordering = ["-total_score"]

    def __str__(self):
        return f"Job#{self.job_id} | Candidate#{self.candidate_id} → {self.total_score:.1f}"


class RankingRun(models.Model):
    """Tracks each ranking execution for a job."""
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE, related_name="ranking_runs")
    status = models.CharField(
        max_length=20,
        choices=[("running", "Running"), ("done", "Done"), ("error", "Error")],
        default="running",
    )
    total_candidates = models.PositiveIntegerField(default=0)
    processed_candidates = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"RankingRun Job#{self.job_id} — {self.status}"
