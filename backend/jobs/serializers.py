from rest_framework import serializers
from .models import Job


class JobSerializer(serializers.ModelSerializer):
    ranked_count = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            "id", "title", "description", "required_skills", "preferred_skills",
            "min_experience_years", "education_required", "department", "location",
            "employment_type", "is_active", "created_at", "updated_at",
            "parsed_requirements", "ranked_count",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "parsed_requirements"]

    def get_ranked_count(self, obj):
        return obj.rankingresult_set.count()


class JobCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = [
            "id", "title", "description", "required_skills", "preferred_skills",
            "min_experience_years", "education_required", "department",
            "location", "employment_type",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        from ai_pipeline.ranker import parse_jd
        job = super().create(validated_data)
        # Auto-parse JD on creation
        try:
            parsed = parse_jd(job.description)
            job.parsed_requirements = parsed
            if not job.required_skills and parsed.get("required_skills"):
                job.required_skills = parsed["required_skills"]
            job.save(update_fields=["parsed_requirements", "required_skills"])
        except Exception:
            pass
        return job
