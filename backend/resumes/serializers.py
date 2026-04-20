from rest_framework import serializers
from .models import Resume


class ResumeSerializer(serializers.ModelSerializer):
    file_size_kb = serializers.ReadOnlyField()
    candidate_name = serializers.SerializerMethodField()

    class Meta:
        model = Resume
        fields = [
            "id", "filename", "file_type", "job_role", "batch_date",
            "upload_date", "status", "parse_confidence", "parsed_sections",
            "error_message", "content_hash", "file_size_kb", "candidate_name",
        ]
        read_only_fields = [
            "id", "filename", "file_type", "batch_date", "upload_date",
            "status", "parse_confidence", "parsed_sections", "error_message",
            "content_hash",
        ]

    def get_candidate_name(self, obj):
        """Extract candidate name from parsed profile if available."""
        try:
            from candidates.models import CandidateProfile
            profile = CandidateProfile.objects.filter(resume=obj).first()
            if profile:
                contact = profile.structured_profile.get("contact", {})
                if isinstance(contact, dict):
                    return contact.get("name", "")
        except Exception:
            pass
        return ""


class ResumeUploadSerializer(serializers.Serializer):
    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=False,
        max_length=100,
    )
    job_role = serializers.CharField(max_length=200, default="General")

    def validate_files(self, files):
        allowed = {".pdf", ".docx", ".jpg", ".jpeg", ".png"}
        max_size = 10 * 1024 * 1024  # 10 MB

        for f in files:
            ext = "." + f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""
            if ext not in allowed:
                raise serializers.ValidationError(
                    f"File '{f.name}' has unsupported type '{ext}'. "
                    f"Allowed: {', '.join(allowed)}"
                )
            if f.size > max_size:
                raise serializers.ValidationError(
                    f"File '{f.name}' exceeds 10 MB limit."
                )
        return files
