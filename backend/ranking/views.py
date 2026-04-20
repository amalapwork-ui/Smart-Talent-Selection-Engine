import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import RankingResult, RankingRun
from .serializers import RankingResultSerializer, RankingRunSerializer

logger = logging.getLogger(__name__)


class RankingResultViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RankingResult.objects.select_related("job", "candidate", "candidate__resume").all()
    serializer_class = RankingResultSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["job_id", "candidate_id"]

    def get_queryset(self):
        qs = super().get_queryset()
        job_id = self.request.query_params.get("job_id")
        if job_id:
            qs = qs.filter(job_id=job_id)
        min_score = self.request.query_params.get("min_score")
        if min_score:
            try:
                qs = qs.filter(total_score__gte=float(min_score))
            except (ValueError, TypeError):
                pass  # invalid min_score — ignore rather than crash
        # Multi-skill filter: ?skills=python,django (AND logic)
        # Also accepts legacy single ?skill=python for backward compat
        skill_param  = self.request.query_params.get("skill", "").strip()
        skills_param = self.request.query_params.get("skills", "").strip()
        raw = skills_param or skill_param
        if raw:
            required = {s.strip().lower()[:100] for s in raw.split(",") if s.strip()}
            if required:
                # Python-level filter — supports SQLite (no JSONField __contains)
                ids = [
                    r.id for r in qs.select_related("candidate")
                    if required.issubset(set(r.candidate.structured_profile.get("skills") or []))
                ]
                qs = qs.filter(id__in=ids)
        return qs.order_by("-total_score")


class RankingRunViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = RankingRun.objects.select_related("job").all()
    serializer_class = RankingRunSerializer
    filterset_fields = ["job_id", "status"]

    @action(detail=False, methods=["post"], url_path="quick-rank")
    def quick_rank(self, request):
        """
        Synchronous quick ranking for a single JD text + all processed candidates.
        For small batches (< 50 candidates) — use async task for large batches.
        """
        jd_text = request.data.get("jd_text", "")
        job_id = request.data.get("job_id")
        try:
            limit = min(int(request.data.get("limit", 50)), 200)
        except (ValueError, TypeError):
            limit = 50

        if not jd_text:
            return Response({"error": "jd_text is required."}, status=400)

        from candidates.models import CandidateProfile
        from ai_pipeline.ranker import rank_candidates

        qs = CandidateProfile.objects.filter(resume__status="done")
        if job_id:
            qs = qs.filter(resume__job_role=request.data.get("job_role", ""))

        qs = qs[:limit]
        candidates = [
            {"id": c.id, "profile": c.structured_profile} for c in qs
        ]

        results = rank_candidates(candidates, jd_text)
        return Response({
            "results": results[:20],
            "total_processed": len(candidates),
        })
