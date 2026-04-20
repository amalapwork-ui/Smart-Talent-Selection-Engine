from rest_framework import serializers
from .models import CandidateProfile, RecruiterFeedback
from jobs.models import Job


class CandidateProfileSerializer(serializers.ModelSerializer):

    candidate_name = serializers.ReadOnlyField()
    skills = serializers.ReadOnlyField()
    total_experience_years = serializers.ReadOnlyField()
    resume_filename = serializers.SerializerMethodField()
    resume_job_role = serializers.SerializerMethodField()
    resume_url = serializers.SerializerMethodField()
    resume_file_type = serializers.SerializerMethodField()
    latest_score = serializers.SerializerMethodField()
    latest_feedback_action = serializers.SerializerMethodField()

    class Meta:
        model = CandidateProfile
        fields = [
            "id", "resume_id", "resume_filename", "resume_job_role",
            "resume_url", "resume_file_type",
            "structured_profile", "profile_text", "created_at", "updated_at",
            "recruiter_notes", "is_shortlisted", "bias_flags",
            "candidate_name", "skills", "total_experience_years",
            "latest_score", "latest_feedback_action",
        ]
        read_only_fields = [
            "id", "resume_id", "structured_profile", "profile_text",
            "created_at", "updated_at", "bias_flags",
        ]

    def get_resume_filename(self, obj):
        return obj.resume.filename if obj.resume else ""

    def get_resume_job_role(self, obj):
        return obj.resume.job_role if obj.resume else ""

    def get_resume_url(self, obj):
        try:
            return obj.resume.file.url if obj.resume and obj.resume.file else None
        except Exception:
            return None

    def get_resume_file_type(self, obj):
        return obj.resume.file_type if obj.resume else ""

    def get_latest_score(self, obj):
        result = obj.rankingresult_set.order_by("-created_at").first()
        if result:
            return {"total": result.total_score, "job_title": result.job.title}
        return None

    def get_latest_feedback_action(self, obj):
        fb = obj.feedback.order_by("-created_at").first()
        return fb.action if fb else None


class RecruiterFeedbackSerializer(serializers.ModelSerializer):
    candidate_id = serializers.PrimaryKeyRelatedField(
        queryset=CandidateProfile.objects.all(), source="candidate"
    )
    job_id = serializers.PrimaryKeyRelatedField(
        queryset=Job.objects.all(), source="job"
    )

    class Meta:
        model = RecruiterFeedback
        fields = ["id", "candidate_id", "job_id", "action", "notes", "created_at"]
        read_only_fields = ["id", "created_at"]
