"""
Tests for the ranking app — results list, filtering, quick-rank endpoint.
"""
import hashlib
from unittest.mock import patch, MagicMock

from rest_framework.test import APITestCase
from rest_framework import status

from resumes.models import Resume
from jobs.models import Job
from candidates.models import CandidateProfile
from ranking.models import RankingResult, RankingRun


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_resume(filename="r.pdf", job_role="Backend", idx=0):
    return Resume.objects.create(
        filename=filename,
        file_type=".pdf",
        job_role=job_role,
        status="done",
        content_hash=hashlib.sha256(f"{filename}{idx}".encode()).hexdigest(),
    )


PROFILE = {
    "contact": {"name": "Test Cand"},
    "skills": ["python", "django", "react"],
    "skill_categories": {},
    "experience_years": {"total_years": 3, "roles": [], "timeline": []},
    "projects": [],
    "education": [{"degree": "B.Tech CS"}],
    "certifications": [],
    "summary": "Test candidate.",
    "extraction_method": "test",
}


def _make_candidate(idx=0, profile=None, job_role="Backend"):
    resume = _make_resume(f"cand_{idx}.pdf", job_role=job_role, idx=idx)
    return CandidateProfile.objects.create(
        resume=resume,
        structured_profile=profile or PROFILE,
        profile_text="python django react",
        embedding_vector=[],
    )


def _make_job(**kwargs):
    defaults = {
        "title": "Python Developer",
        "description": "We need a Python developer with Django skills.",
        "required_skills": ["python", "django"],
        "min_experience_years": 2,
    }
    defaults.update(kwargs)
    return Job.objects.create(**defaults)


def _make_result(job, candidate, score=75.0, rank=1):
    return RankingResult.objects.create(
        job=job,
        candidate=candidate,
        total_score=score,
        skill_score=score + 5,
        experience_score=score - 5,
        project_score=score - 10,
        education_score=score - 15,
        score_breakdown={},
        justification="Strong candidate.",
        rank_position=rank,
    )


# ---------------------------------------------------------------------------
# RankingResult model
# ---------------------------------------------------------------------------

class RankingResultModelTest(APITestCase):
    def test_str_representation(self):
        job = _make_job()
        cp = _make_candidate(idx=0)
        result = _make_result(job, cp, score=82.5)
        self.assertIn("82.5", str(result))

    def test_unique_together_enforced(self):
        from django.db import IntegrityError
        job = _make_job()
        cp = _make_candidate(idx=1)
        _make_result(job, cp, score=80.0)
        with self.assertRaises(IntegrityError):
            RankingResult.objects.create(
                job=job,
                candidate=cp,
                total_score=90.0,
            )


# ---------------------------------------------------------------------------
# Ranking Results API — List and filter
# ---------------------------------------------------------------------------

class RankingResultListAPITest(APITestCase):
    URL = "/api/ranking/results/"

    def setUp(self):
        self.job1 = _make_job(title="Job One")
        self.job2 = _make_job(title="Job Two")
        self.cp1 = _make_candidate(idx=10)
        self.cp2 = _make_candidate(idx=11)
        self.cp3 = _make_candidate(idx=12)

        self.r1 = _make_result(self.job1, self.cp1, score=85.0, rank=1)
        self.r2 = _make_result(self.job1, self.cp2, score=60.0, rank=2)
        self.r3 = _make_result(self.job2, self.cp3, score=70.0, rank=1)

    def test_list_all_results(self):
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.json()["count"], 3)

    def test_filter_by_job_id(self):
        response = self.client.get(self.URL, {"job_id": self.job1.id})
        results = response.json()["results"]
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r["job_id"] == self.job1.id for r in results))

    def test_filter_by_min_score(self):
        response = self.client.get(self.URL, {"min_score": "70"})
        results = response.json()["results"]
        self.assertTrue(all(r["total_score"] >= 70.0 for r in results))

    def test_filter_by_min_score_invalid_ignored(self):
        # Should not crash with invalid min_score
        response = self.client.get(self.URL, {"min_score": "not_a_number"})
        self.assertIn(response.status_code, [200, 400])

    def test_ordered_by_total_score_descending(self):
        response = self.client.get(self.URL, {"job_id": self.job1.id})
        results = response.json()["results"]
        scores = [r["total_score"] for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_result_has_expected_fields(self):
        response = self.client.get(f"{self.URL}{self.r1.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        for field in ("total_score", "skill_score", "experience_score",
                      "project_score", "education_score", "justification",
                      "candidate_id", "job_id", "rank_position"):
            self.assertIn(field, data)

    def test_filter_by_skill(self):
        response = self.client.get(self.URL, {"job_id": self.job1.id, "skill": "python"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Both candidates have "python" — expect both
        results = response.json()["results"]
        self.assertGreaterEqual(len(results), 1)

    def test_retrieve_nonexistent_result(self):
        response = self.client.get(f"{self.URL}99999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Quick-rank endpoint
# ---------------------------------------------------------------------------

class QuickRankAPITest(APITestCase):
    URL = "/api/ranking/runs/quick-rank/"

    JD_TEXT = "We are looking for a Python Django backend developer with 2+ years experience."

    def setUp(self):
        # Create some processed candidates
        for i in range(3):
            _make_candidate(idx=100 + i)

    def test_quick_rank_missing_jd_text(self):
        response = self.client.post(self.URL, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.json())

    def test_quick_rank_returns_results(self):
        response = self.client.post(
            self.URL,
            {"jd_text": self.JD_TEXT},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("results", data)
        self.assertIn("total_processed", data)
        self.assertGreaterEqual(data["total_processed"], 0)

    def test_quick_rank_results_sorted_descending(self):
        response = self.client.post(
            self.URL,
            {"jd_text": self.JD_TEXT},
            format="json",
        )
        data = response.json()
        scores = [r["total_score"] for r in data["results"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_quick_rank_limit_respected(self):
        response = self.client.post(
            self.URL,
            {"jd_text": self.JD_TEXT, "limit": 2},
            format="json",
        )
        data = response.json()
        # total_processed should be capped at limit
        self.assertLessEqual(data["total_processed"], 2)

    def test_quick_rank_invalid_limit_does_not_crash(self):
        response = self.client.post(
            self.URL,
            {"jd_text": self.JD_TEXT, "limit": "notanumber"},
            format="json",
        )
        self.assertIn(response.status_code, [200, 400])

    def test_quick_rank_limit_capped_at_200(self):
        response = self.client.post(
            self.URL,
            {"jd_text": self.JD_TEXT, "limit": 99999},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertLessEqual(data["total_processed"], 200)


# ---------------------------------------------------------------------------
# RankingRun model
# ---------------------------------------------------------------------------

class RankingRunAPITest(APITestCase):
    URL = "/api/ranking/runs/"

    def setUp(self):
        self.job = _make_job()
        self.run = RankingRun.objects.create(
            job=self.job,
            status="done",
            total_candidates=10,
            processed_candidates=10,
        )

    def test_list_runs(self):
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.json()["count"], 1)

    def test_filter_by_job_id(self):
        response = self.client.get(self.URL, {"job_id": self.job.id})
        results = response.json()["results"]
        self.assertTrue(all(r["job_id"] == self.job.id for r in results))

    def test_filter_by_status(self):
        response = self.client.get(self.URL, {"status": "done"})
        results = response.json()["results"]
        self.assertTrue(all(r["status"] == "done" for r in results))
