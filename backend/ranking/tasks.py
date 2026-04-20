import logging
from datetime import datetime, timezone
from celery import shared_task
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def rank_candidates_task(self, job_id: int):
    """
    Async task: rank all processed candidates for a given job.
    Updates RankingResult records and assigns rank positions.
    """
    from jobs.models import Job
    from candidates.models import CandidateProfile
    from ranking.models import RankingResult, RankingRun
    from ai_pipeline.ranker import rank_candidates

    try:
        job = Job.objects.get(id=job_id)
    except Job.DoesNotExist:
        logger.error(f"Job {job_id} not found.")
        return

    run = RankingRun.objects.create(job=job, status="running")

    try:
        candidates_qs = CandidateProfile.objects.filter(
            resume__status="done"
        ).select_related("resume")

        total = candidates_qs.count()
        run.total_candidates = total
        run.save(update_fields=["total_candidates"])

        if total == 0:
            run.status = "done"
            run.finished_at = datetime.now(timezone.utc)
            run.save(update_fields=["status", "finished_at"])
            return {"job_id": job_id, "ranked": 0}

        # Prepare candidate data
        candidates_data = [
            {"id": c.id, "profile": c.structured_profile}
            for c in candidates_qs
        ]

        # Run ranking engine
        ranked = rank_candidates(candidates_data, job.description)

        # Bulk upsert — one query instead of N round-trips
        rows = [
            RankingResult(
                job=job,
                candidate_id=result["candidate_id"],
                total_score=result["total_score"],
                skill_score=result["skill_score"],
                experience_score=result["experience_score"],
                project_score=result["project_score"],
                education_score=result["education_score"],
                score_breakdown=result.get("score_breakdown", {}),
                justification=result.get("justification", ""),
                rank_position=position,
            )
            for position, result in enumerate(ranked, start=1)
        ]
        with transaction.atomic():
            RankingResult.objects.bulk_create(
                rows,
                update_conflicts=True,
                unique_fields=["job", "candidate"],
                update_fields=[
                    "total_score", "skill_score", "experience_score",
                    "project_score", "education_score", "score_breakdown",
                    "justification", "rank_position",
                ],
            )
        run.status = "done"
        run.processed_candidates = len(ranked)
        run.finished_at = datetime.now(timezone.utc)
        run.save(update_fields=["status", "processed_candidates", "finished_at"])

        logger.info(f"Ranked {len(ranked)} candidates for Job#{job_id}")
        return {"job_id": job_id, "ranked": len(ranked)}

    except Exception as exc:
        logger.exception(f"Ranking task failed for Job#{job_id}: {exc}")
        run.status = "error"
        run.error_message = str(exc)[:500]
        run.finished_at = datetime.now(timezone.utc)
        run.save(update_fields=["status", "error_message", "finished_at"])
        raise
