import logging
import threading
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Job
from .serializers import JobSerializer, JobCreateSerializer

logger = logging.getLogger(__name__)


class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["is_active", "employment_type", "department"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return JobCreateSerializer
        return JobSerializer

    @action(detail=True, methods=["post"], url_path="run-ranking")
    def run_ranking(self, request, pk=None):
        """
        Trigger ranking of all eligible candidates for this job.
        Queues async ranking task.
        """
        job = self.get_object()
        from ranking.tasks import rank_candidates_task
        threading.Thread(target=rank_candidates_task.delay, args=(job.id,), daemon=True).start()
        return Response({
            "message": "Ranking started.",
            "job_id": job.id,
        })

    @action(detail=True, methods=["get"], url_path="suggest-jd")
    def suggest_jd(self, request, pk=None):
        """
        JD Optimization: suggest improvements to the job description.
        """
        job = self.get_object()
        from django.conf import settings
        api_key = settings.GROQ_API_KEY
        if not api_key:
            return Response({"error": "GROQ_API_KEY not configured."}, status=503)

        try:
            from groq import Groq
            client = Groq(api_key=api_key)
            response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "You are a talent acquisition expert."},
                    {
                        "role": "user",
                        "content": (
                            f"Review this job description and suggest 3-5 improvements "
                            f"to attract better candidates (clarity, bias removal, skill phrasing):\n\n"
                            f"{job.description[:3000]}"
                        ),
                    },
                ],
                temperature=0.5,
                max_tokens=500,
            )
            suggestion = response.choices[0].message.content
            return Response({"suggestions": suggestion})
        except Exception as e:
            return Response({"error": str(e)}, status=500)
