import hashlib
import logging
import os
import threading
from django.conf import settings
from django.db.models import Count, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Resume
from .serializers import ResumeSerializer, ResumeUploadSerializer

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = getattr(settings, "ALLOWED_RESUME_EXTENSIONS", [".pdf", ".docx", ".jpg", ".jpeg", ".png"])
MAX_UPLOAD_SIZE = getattr(settings, "MAX_UPLOAD_SIZE", 10 * 1024 * 1024)


def _safe_filename(name: str) -> str:
    """Strip path separators and null bytes to prevent path traversal."""
    return os.path.basename(name).replace("\x00", "").strip()


class ResumeViewSet(viewsets.ModelViewSet):
    queryset = Resume.objects.all()
    serializer_class = ResumeSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["status", "job_role", "file_type"]

    def get_serializer_class(self):
        if self.action == "bulk_upload":
            return ResumeUploadSerializer
        return ResumeSerializer

    @action(detail=False, methods=["post"], url_path="upload")
    def bulk_upload(self, request):
        """
        Bulk resume upload endpoint.
        Accepts multiple files + job_role, queues async parsing.
        """
        serializer = ResumeUploadSerializer(data={
            "files": request.FILES.getlist("files"),
            "job_role": request.data.get("job_role", "General"),
        })
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        files = serializer.validated_data["files"]
        job_role = serializer.validated_data["job_role"]
        created_ids = []
        duplicates = []
        errors = []

        for f in files:
            original_name = getattr(f, "name", "unknown")
            try:
                # ── Security: sanitize filename (prevent path traversal) ──────
                safe_name = _safe_filename(original_name)
                if not safe_name:
                    errors.append({"filename": original_name, "error": "Invalid filename."})
                    continue

                # ── Security: extension whitelist ─────────────────────────────
                ext = ("." + safe_name.rsplit(".", 1)[-1].lower()) if "." in safe_name else ""
                if ext not in ALLOWED_EXTENSIONS:
                    errors.append({
                        "filename": original_name,
                        "error": f"File type '{ext}' is not allowed. Accepted: {', '.join(ALLOWED_EXTENSIONS)}",
                    })
                    continue

                # ── Security: read once, check size before hashing ────────────
                content = f.read()
                if len(content) > MAX_UPLOAD_SIZE:
                    errors.append({
                        "filename": original_name,
                        "error": f"File exceeds {MAX_UPLOAD_SIZE // (1024 * 1024)} MB limit.",
                    })
                    continue
                f.seek(0)

                # ── Duplicate detection via SHA-256 ───────────────────────────
                content_hash = hashlib.sha256(content).hexdigest()
                existing = Resume.objects.filter(content_hash=content_hash).first()
                if existing:
                    duplicates.append({
                        "filename": original_name,
                        "duplicate_of": existing.id,
                    })
                    continue

                resume = Resume.objects.create(
                    file=f,
                    filename=safe_name,
                    file_type=ext,
                    job_role=job_role,
                    status="pending",
                    content_hash=content_hash,
                )
                created_ids.append(resume.id)

                # Run parsing in a daemon thread so the HTTP response is immediate.
                # With CELERY_TASK_ALWAYS_EAGER the task executes synchronously
                # inside the thread — no broker or worker process required.
                from resumes.tasks import parse_resume_task
                threading.Thread(
                    target=parse_resume_task.delay,
                    args=(resume.id,),
                    daemon=True,
                ).start()

            except Exception as e:
                logger.error(f"Upload error for {original_name}: {e}")
                errors.append({"filename": original_name, "error": str(e)})

        return Response({
            "created": created_ids,
            "duplicates": duplicates,
            "errors": errors,
            "total_queued": len(created_ids),
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        """Dashboard stats — counts by status and job role."""
        qs = Resume.objects.all()
        total = qs.count()
        by_status = dict(qs.values_list("status").annotate(c=Count("id")).values_list("status", "c"))
        by_role = list(
            qs.values("job_role").annotate(count=Count("id")).order_by("-count")[:10]
        )
        return Response({
            "total": total,
            "by_status": by_status,
            "by_role": by_role,
        })

    @action(detail=True, methods=["post"], url_path="reparse")
    def reparse(self, request, pk=None):
        """Manually trigger re-parsing for a resume."""
        resume = self.get_object()
        resume.status = "pending"
        resume.error_message = ""
        resume.save(update_fields=["status", "error_message"])
        from resumes.tasks import parse_resume_task
        threading.Thread(target=parse_resume_task.delay, args=(resume.id,), daemon=True).start()
        return Response({"message": "Reparse queued.", "id": resume.id})
