from rest_framework import serializers
from .models import RankingResult, RankingRun


class RankingResultSerializer(serializers.ModelSerializer):
    candidate_name = serializers.SerializerMethodField()
    candidate_skills = serializers.SerializerMethodField()
    candidate_experience_years = serializers.SerializerMethodField()
    resume_filename = serializers.SerializerMethodField()
    resume_id = serializers.SerializerMethodField()

    class Meta:
        model = RankingResult
        fields = [
            "id", "job_id", "candidate_id",
            "total_score", "skill_score", "experience_score",
            "project_score", "education_score", "score_breakdown",
            "justification", "rank_position", "created_at",
            "candidate_name", "candidate_skills", "candidate_experience_years",
            "resume_filename", "resume_id",
        ]

    def get_candidate_name(self, obj):
        return obj.candidate.candidate_name

    def get_candidate_skills(self, obj):
        return obj.candidate.skills[:10]

    def get_candidate_experience_years(self, obj):
        return obj.candidate.total_experience_years

    def get_resume_filename(self, obj):
        return obj.candidate.resume.filename if obj.candidate.resume else ""

    def get_resume_id(self, obj):
        return obj.candidate.resume_id


class RankingRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = RankingRun
        fields = [
            "id", "job_id", "status", "total_candidates",
            "processed_candidates", "error_message", "started_at", "finished_at",
        ]
