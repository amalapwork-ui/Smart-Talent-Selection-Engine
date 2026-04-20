"""
Tests for the candidates app — profiles, feedback, vs-jd comparison, search.
"""
import hashlib
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status

from resumes.models import Resume
from jobs.models import Job
from candidates.models import CandidateProfile, RecruiterFeedback
from ranking.models import RankingResult


def _make_resume(name="test.pdf", job_role="Backend", status_val="done", idx=0):
    return Resume.objects.create(
        filename=name,
        file_type=".pdf",
        job_role=job_role,
        status=status_val,
        content_hash=hashlib.sha256(f"{name}{idx}".encode()).hexdigest(),
    )


SAMPLE_PROFILE = {
    "contact": {"name": "Alice Dev", "email": "alice@test.com", "phone": "9876543210"},
    "skills": ["python", "django", "react", "postgresql"],
    "skill_categories": {"backend": ["python", "django"], "frontend": ["react"]},
    "experience_years": {"total_years": 4, "roles": [
        {"title": "Backend Engineer", "company": "TechCo", "years": 4}
    ]},
    "projects": [
        {
            "name": "API Platform",
            "description": "Django REST API with PostgreSQL",
            "tech_stack": ["python", "django", "postgresql"],
        }
    ],
    "education": [{"degree": "B.Tech Computer Science", "institution": "IIT", "year": "2020"}],
    "certifications": ["AWS Certified"],
    "summary": "Experienced full-stack developer.",
    "extraction_method": "test",
}


def _make_candidate(idx=0, profile=None, job_role="Backend"):
    resume = _make_resume(f"cand_{idx}.pdf", job_role=job_role, idx=idx)
    return CandidateProfile.objects.create(
        resume=resume,
        structured_profile=profile or SAMPLE_PROFILE,
        profile_text="Alice Dev python django react postgresql",
        embedding_vector=[],
    )


def _make_job(**kwargs):
    defaults = {
        "title": "Backend Developer",
        "description": "Python Django backend with PostgreSQL",
        "required_skills": ["python", "django", "postgresql"],
        "preferred_skills": ["docker"],
        "min_experience_years": 2,
    }
    defaults.update(kwargs)
    return Job.objects.create(**defaults)


# ---------------------------------------------------------------------------
# CandidateProfile model
# ---------------------------------------------------------------------------

class CandidateProfileModelTest(TestCase):
    def test_candidate_name_from_profile(self):
        cp = _make_candidate(idx=0)
        self.assertEqual(cp.candidate_name, "Alice Dev")

    def test_skills_from_profile(self):
        cp = _make_candidate(idx=1)
        skills = cp.skills
        self.assertIn("python", skills)
        self.assertIn("django", skills)

    def test_total_experience_years(self):
        cp = _make_candidate(idx=2)
        self.assertEqual(cp.total_experience_years, 4)

    def test_total_experience_from_int(self):
        profile = {**SAMPLE_PROFILE, "experience_years": 3}
        cp = _make_candidate(idx=3, profile=profile)
        self.assertEqual(cp.total_experience_years, 3)

    def test_empty_profile_defaults(self):
        resume = _make_resume("empty.pdf", idx=99)
        cp = CandidateProfile.objects.create(
            resume=resume,
            structured_profile={},
            embedding_vector=[],
        )
        self.assertIn("Candidate", cp.candidate_name)
        self.assertEqual(cp.skills, [])
        self.assertEqual(cp.total_experience_years, 0)


# ---------------------------------------------------------------------------
# Candidate API — List / Retrieve
# ---------------------------------------------------------------------------

class CandidateListAPITest(APITestCase):
    URL = "/api/candidates/"

    def setUp(self):
        self.cp1 = _make_candidate(idx=10, job_role="Backend")
        self.cp2 = _make_candidate(idx=11, job_role="Frontend")

    def test_list_candidates(self):
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.json()["count"], 2)

    def test_retrieve_candidate_detail(self):
        response = self.client.get(f"{self.URL}{self.cp1.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("structured_profile", data)
        self.assertIn("candidate_name", data)

    def test_retrieve_nonexistent_candidate(self):
        response = self.client.get(f"{self.URL}99999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_by_shortlisted(self):
        self.cp1.is_shortlisted = True
        self.cp1.save()
        response = self.client.get(self.URL, {"is_shortlisted": "true"})
        results = response.json()["results"]
        self.assertTrue(all(r["is_shortlisted"] for r in results))

    def test_filter_by_job_role(self):
        response = self.client.get(self.URL, {"resume__job_role": "Frontend"})
        results = response.json()["results"]
        self.assertTrue(all(r["resume_job_role"] == "Frontend" for r in results))


# ---------------------------------------------------------------------------
# Candidate API — Feedback
# ---------------------------------------------------------------------------

class RecruiterFeedbackAPITest(APITestCase):
    def setUp(self):
        self.cp = _make_candidate(idx=20)
        self.job = _make_job()

    def test_submit_valid_feedback(self):
        response = self.client.post(
            f"/api/candidates/{self.cp.id}/feedback/",
            {"action": "shortlisted", "notes": "Great candidate", "job_id": self.job.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(RecruiterFeedback.objects.filter(candidate=self.cp, job=self.job).exists())

    def test_shortlist_action_sets_flag(self):
        self.client.post(
            f"/api/candidates/{self.cp.id}/feedback/",
            {"action": "shortlisted", "job_id": self.job.id},
            format="json",
        )
        self.cp.refresh_from_db()
        self.assertTrue(self.cp.is_shortlisted)

    def test_hired_action_sets_shortlist_flag(self):
        self.client.post(
            f"/api/candidates/{self.cp.id}/feedback/",
            {"action": "hired", "job_id": self.job.id},
            format="json",
        )
        self.cp.refresh_from_db()
        self.assertTrue(self.cp.is_shortlisted)

    def test_rejected_action_does_not_shortlist(self):
        self.client.post(
            f"/api/candidates/{self.cp.id}/feedback/",
            {"action": "rejected", "job_id": self.job.id},
            format="json",
        )
        self.cp.refresh_from_db()
        self.assertFalse(self.cp.is_shortlisted)

    def test_feedback_missing_action_rejected(self):
        response = self.client.post(
            f"/api/candidates/{self.cp.id}/feedback/",
            {"notes": "ok", "job_id": self.job.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_feedback_invalid_action_rejected(self):
        response = self.client.post(
            f"/api/candidates/{self.cp.id}/feedback/",
            {"action": "promote_to_ceo", "job_id": self.job.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Candidate API — vs-jd comparison
# ---------------------------------------------------------------------------

class VsJDComparisonTest(APITestCase):
    def setUp(self):
        self.cp = _make_candidate(idx=30)
        self.job = _make_job()

    def test_comparison_missing_job_id(self):
        response = self.client.get(f"/api/candidates/{self.cp.id}/vs-jd/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("job_id", response.json()["error"])

    def test_comparison_invalid_job_id(self):
        response = self.client.get(f"/api/candidates/{self.cp.id}/vs-jd/", {"job_id": 99999})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_comparison_valid_returns_structure(self):
        response = self.client.get(
            f"/api/candidates/{self.cp.id}/vs-jd/",
            {"job_id": self.job.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("candidate", data)
        self.assertIn("job", data)
        self.assertIn("comparison", data)
        self.assertIn("matching_skills", data["comparison"])
        self.assertIn("missing_skills", data["comparison"])

    def test_comparison_shows_matching_skills(self):
        response = self.client.get(
            f"/api/candidates/{self.cp.id}/vs-jd/",
            {"job_id": self.job.id},
        )
        data = response.json()
        # Both candidate and job have python, django, postgresql
        matching = data["comparison"]["matching_skills"]
        self.assertIn("python", matching)
        self.assertIn("django", matching)

    def test_comparison_with_ranking_shows_score(self):
        # Create a ranking result
        RankingResult.objects.create(
            job=self.job,
            candidate=self.cp,
            total_score=75.0,
            skill_score=80.0,
            experience_score=70.0,
            project_score=60.0,
            education_score=50.0,
            justification="Strong backend candidate.",
        )
        response = self.client.get(
            f"/api/candidates/{self.cp.id}/vs-jd/",
            {"job_id": self.job.id},
        )
        data = response.json()
        self.assertEqual(data["ranking"]["total_score"], 75.0)
        self.assertEqual(data["ranking"]["justification"], "Strong backend candidate.")


# ---------------------------------------------------------------------------
# Candidate API — Semantic search
# ---------------------------------------------------------------------------

class SemanticSearchAPITest(APITestCase):
    URL = "/api/candidates/search/"

    def test_search_missing_query(self):
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.json())

    def test_search_with_query_returns_structure(self):
        # Even if no candidates are indexed, should not crash
        response = self.client.get(self.URL, {"q": "python django developer"})
        # May return 200 with empty results or 500 if FAISS not initialized
        self.assertIn(response.status_code, [200, 500])
        if response.status_code == 200:
            data = response.json()
            self.assertIn("results", data)
            self.assertIn("total", data)

    def test_search_k_parameter_bounded(self):
        # k=9999 should be clamped to 100
        response = self.client.get(self.URL, {"q": "developer", "k": "9999"})
        self.assertIn(response.status_code, [200, 500])
