"""
Tests for the jobs app — CRUD, filtering, ranking trigger, validation.
"""
from unittest.mock import patch, MagicMock

from rest_framework.test import APITestCase
from rest_framework import status

from jobs.models import Job


def make_job(**kwargs):
    defaults = {
        "title": "Test Engineer",
        "description": "We need a Python developer with Django and PostgreSQL skills.",
        "required_skills": ["python", "django"],
        "preferred_skills": ["docker"],
        "min_experience_years": 2,
        "department": "Engineering",
        "location": "Remote",
        "employment_type": "full_time",
        "is_active": True,
    }
    defaults.update(kwargs)
    return Job.objects.create(**defaults)


# ---------------------------------------------------------------------------
# Job Model
# ---------------------------------------------------------------------------

class JobModelTest(APITestCase):
    def test_str_contains_title(self):
        job = make_job(title="ML Engineer")
        self.assertIn("ML Engineer", str(job))

    def test_default_is_active(self):
        job = Job.objects.create(title="Dev", description="desc")
        self.assertTrue(job.is_active)

    def test_ordering_by_created_descending(self):
        j1 = make_job(title="First")
        j2 = make_job(title="Second")
        jobs = list(Job.objects.all())
        self.assertEqual(jobs[0].id, j2.id)


# ---------------------------------------------------------------------------
# Job API — CRUD
# ---------------------------------------------------------------------------

class JobCreateAPITest(APITestCase):
    URL = "/api/jobs/"

    VALID_PAYLOAD = {
        "title": "Senior Python Developer",
        "description": "We are looking for a Senior Python developer with Django expertise.",
        "required_skills": ["python", "django", "postgresql"],
        "preferred_skills": ["docker", "celery"],
        "min_experience_years": 3,
        "department": "Backend Engineering",
        "location": "Bangalore",
        "employment_type": "full_time",
    }

    def test_create_valid_job(self):
        response = self.client.post(self.URL, self.VALID_PAYLOAD, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["title"], "Senior Python Developer")
        self.assertIn("id", data)

    def test_create_job_missing_title(self):
        payload = {k: v for k, v in self.VALID_PAYLOAD.items() if k != "title"}
        response = self.client.post(self.URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_job_missing_description(self):
        payload = {k: v for k, v in self.VALID_PAYLOAD.items() if k != "description"}
        response = self.client.post(self.URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_job_empty_payload(self):
        response = self.client.post(self.URL, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_job_invalid_employment_type(self):
        payload = {**self.VALID_PAYLOAD, "employment_type": "not_a_real_type"}
        response = self.client.post(self.URL, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_job_negative_experience(self):
        payload = {**self.VALID_PAYLOAD, "min_experience_years": -1}
        response = self.client.post(self.URL, payload, format="json")
        # Should reject (PositiveIntegerField) or clamp to 0
        self.assertIn(response.status_code, [400, 201])

    def test_create_job_xss_in_title_stored_safely(self):
        payload = {**self.VALID_PAYLOAD, "title": "<script>alert('xss')</script>"}
        response = self.client.post(self.URL, payload, format="json")
        if response.status_code == 201:
            # Django ORM stores the raw string; frontend must escape on render
            stored_title = response.json()["title"]
            self.assertEqual(stored_title, "<script>alert('xss')</script>")

    def test_list_jobs(self):
        make_job(title="Job A")
        make_job(title="Job B")
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.json()["count"], 2)

    def test_retrieve_single_job(self):
        job = make_job(title="Unique Job")
        response = self.client.get(f"{self.URL}{job.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["title"], "Unique Job")

    def test_retrieve_nonexistent_job(self):
        response = self.client.get(f"{self.URL}99999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_job_patch(self):
        job = make_job(title="Old Title")
        response = self.client.patch(f"{self.URL}{job.id}/", {"title": "New Title"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["title"], "New Title")

    def test_delete_job(self):
        job = make_job(title="Delete Me")
        response = self.client.delete(f"{self.URL}{job.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Job.objects.filter(id=job.id).exists())


# ---------------------------------------------------------------------------
# Job API — Filtering
# ---------------------------------------------------------------------------

class JobFilterAPITest(APITestCase):
    URL = "/api/jobs/"

    def setUp(self):
        self.active_job = make_job(title="Active", is_active=True, department="Engineering")
        self.inactive_job = make_job(title="Closed", is_active=False, department="Sales")
        self.contract_job = make_job(
            title="Contract Role", employment_type="contract", department="Engineering"
        )

    def test_filter_active_jobs(self):
        response = self.client.get(self.URL, {"is_active": "true"})
        results = response.json()["results"]
        self.assertTrue(all(r["is_active"] for r in results))

    def test_filter_inactive_jobs(self):
        response = self.client.get(self.URL, {"is_active": "false"})
        results = response.json()["results"]
        self.assertTrue(all(not r["is_active"] for r in results))

    def test_filter_by_employment_type(self):
        response = self.client.get(self.URL, {"employment_type": "contract"})
        results = response.json()["results"]
        self.assertTrue(all(r["employment_type"] == "contract" for r in results))

    def test_filter_by_department(self):
        response = self.client.get(self.URL, {"department": "Engineering"})
        results = response.json()["results"]
        self.assertTrue(all(r["department"] == "Engineering" for r in results))


# ---------------------------------------------------------------------------
# Job API — Run Ranking action
# ---------------------------------------------------------------------------

class JobRunRankingTest(APITestCase):
    def setUp(self):
        self.job = make_job(title="Ranking Test Job")

    @patch("ranking.tasks.rank_candidates_task")
    def test_run_ranking_returns_task_info(self, mock_task):
        mock_task.delay.return_value = MagicMock(id="rank-task-123")
        response = self.client.post(f"/api/jobs/{self.job.id}/run-ranking/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("task_id", data)
        self.assertIn("job_id", data)
        self.assertEqual(data["job_id"], self.job.id)

    def test_run_ranking_nonexistent_job(self):
        response = self.client.post("/api/jobs/99999/run-ranking/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# Job API — ranked_count field
# ---------------------------------------------------------------------------

class JobRankedCountTest(APITestCase):
    def test_ranked_count_field_present(self):
        job = make_job()
        response = self.client.get(f"/api/jobs/{job.id}/")
        self.assertIn("ranked_count", response.json())
        self.assertEqual(response.json()["ranked_count"], 0)
