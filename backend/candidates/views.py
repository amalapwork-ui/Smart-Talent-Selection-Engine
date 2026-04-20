import logging
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import CandidateProfile, RecruiterFeedback
from .serializers import CandidateProfileSerializer, RecruiterFeedbackSerializer

logger = logging.getLogger(__name__)


class CandidateProfileViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = CandidateProfile.objects.select_related("resume").all()
    serializer_class = CandidateProfileSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["is_shortlisted", "resume__job_role"]

    @action(detail=True, methods=["post"], url_path="feedback")
    def submit_feedback(self, request, pk=None):
        """Record (or update) recruiter feedback for a candidate+job pair."""
        candidate = self.get_object()

        # Validate required fields manually so we can use update_or_create
        # (DRF's UniqueTogetherValidator would block updates otherwise)
        action = request.data.get("action", "").strip()
        notes = request.data.get("notes", "")
        job_id = request.data.get("job_id")

        valid_actions = {"shortlisted", "rejected", "interview", "hired"}
        if not action:
            return Response({"error": "action is required."}, status=status.HTTP_400_BAD_REQUEST)
        if action not in valid_actions:
            return Response(
                {"error": f"action must be one of: {', '.join(sorted(valid_actions))}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not job_id:
            return Response({"error": "job_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        from jobs.models import Job
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        obj, created = RecruiterFeedback.objects.update_or_create(
            candidate=candidate,
            job=job,
            defaults={"action": action, "notes": notes},
        )

        if action in ("shortlisted", "interview", "hired"):
            candidate.is_shortlisted = True
        elif action == "rejected":
            candidate.is_shortlisted = False
        candidate.save(update_fields=["is_shortlisted"])

        serializer = RecruiterFeedbackSerializer(obj)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="vs-jd")
    def compare_with_jd(self, request, pk=None):
        """
        Side-by-side resume vs JD comparison.
        Query param: ?job_id=<id>
        """
        candidate = self.get_object()
        job_id = request.query_params.get("job_id")
        if not job_id:
            return Response({"error": "job_id query param required."}, status=400)

        from jobs.models import Job
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({"error": "Job not found."}, status=404)

        from ranking.models import RankingResult
        ranking = RankingResult.objects.filter(candidate=candidate, job=job).first()

        profile = candidate.structured_profile
        required_skills = set(job.required_skills or [])
        candidate_skills = set(profile.get("skills", []))

        return Response({
            "candidate": {
                "name": candidate.candidate_name,
                "skills": list(candidate_skills),
                "experience_years": candidate.total_experience_years,
                "education": profile.get("education", []),
                "certifications": profile.get("certifications", []),
                "summary": profile.get("summary", ""),
            },
            "job": {
                "title": job.title,
                "required_skills": list(required_skills),
                "min_experience": job.min_experience_years,
                "education_required": job.education_required,
            },
            "comparison": {
                "matching_skills": sorted(candidate_skills & required_skills),
                "missing_skills": sorted(required_skills - candidate_skills),
                "extra_skills": sorted(candidate_skills - required_skills),
                "experience_gap": max(0, job.min_experience_years - candidate.total_experience_years),
            },
            "ranking": {
                "total_score":      ranking.total_score      if ranking else None,
                "skill_score":      ranking.skill_score      if ranking else None,
                "experience_score": ranking.experience_score if ranking else None,
                "project_score":    ranking.project_score    if ranking else None,
                "education_score":  ranking.education_score  if ranking else None,
                "justification":    ranking.justification    if ranking else None,
                "score_breakdown":  ranking.score_breakdown  if ranking else None,
            },
        })

    @action(detail=False, methods=["get"], url_path="search")
    def semantic_search(self, request):
        """
        Semantic search across all candidates using FAISS.
        Query param: ?q=<search text>&k=20
        """
        query = request.query_params.get("q", "").strip()[:500]  # cap query length
        try:
            k = min(int(request.query_params.get("k", 20)), 100)
        except (ValueError, TypeError):
            k = 20
        if not query:
            return Response({"error": "query param 'q' required."}, status=400)

        from ai_pipeline.embeddings import generate_embedding, get_faiss_store
        try:
            embedding = generate_embedding(query)
            store = get_faiss_store()
            results = store.search(embedding, k=k)

            candidate_ids = [r["candidate_id"] for r in results]
            similarity_map = {r["candidate_id"]: r["similarity_score"] for r in results}

            candidates = CandidateProfile.objects.filter(id__in=candidate_ids).select_related("resume")
            serialized = CandidateProfileSerializer(candidates, many=True).data

            # Attach similarity scores
            for item in serialized:
                item["similarity_score"] = round(similarity_map.get(item["id"], 0), 4)

            serialized.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
            return Response({"results": serialized, "total": len(serialized)})
        except Exception as e:
            return Response({"error": str(e)}, status=500)
