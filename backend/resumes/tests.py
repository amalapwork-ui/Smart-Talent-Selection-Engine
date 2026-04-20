"""
Tests for the resumes app — upload, duplicate detection, stats, security.
"""
import hashlib
from io import BytesIO
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status

from resumes.models import Resume


def make_pdf(content=b"%PDF-1.4 test"):
    return SimpleUploadedFile("resume.pdf", content, content_type="application/pdf")


def make_docx(content=b"PK\x03\x04"):
    return SimpleUploadedFile("resume.docx", content,
                              content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class ResumeModelTest(TestCase):
    def _make_resume(self, status="done"):
        return Resume.objects.create(
            filename="test.pdf",
            file_type=".pdf",
            job_role="Backend Developer",
            status=status,
            content_hash=hashlib.sha256(b"unique").hexdigest(),
        )

    def test_str_representation(self):
        r = self._make_resume()
        self.assertIn("test.pdf", str(r))
        self.assertIn("done", str(r))

    def test_file_size_kb_no_file(self):
        r = self._make_resume()
        self.assertEqual(r.file_size_kb, 0)

    def test_default_status_is_pending(self):
        r = Resume(
            filename="x.pdf",
            file_type=".pdf",
            content_hash="abc123",
        )
        self.assertEqual(r.status, "pending")

    def test_ordering_by_upload_date_descending(self):
        r1 = self._make_resume()
        r2 = Resume.objects.create(
            filename="second.pdf", file_type=".pdf",
            content_hash=hashlib.sha256(b"second").hexdigest(),
        )
        resumes = list(Resume.objects.all())
        self.assertEqual(resumes[0].id, r2.id)


# ---------------------------------------------------------------------------
# API — Upload endpoint
# ---------------------------------------------------------------------------

@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
class ResumeUploadAPITest(APITestCase):
    URL = "/api/resumes/upload/"

    @patch("resumes.tasks.parse_resume_task")
    def test_upload_single_pdf(self, mock_task):
        mock_task.delay.return_value = MagicMock(id="task-1")
        response = self.client.post(
            self.URL,
            {"files": make_pdf(), "job_role": "Backend Developer"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["total_queued"], 1)
        self.assertEqual(len(data["created"]), 1)
        self.assertEqual(data["duplicates"], [])
        self.assertEqual(data["errors"], [])

    @patch("resumes.tasks.parse_resume_task")
    def test_upload_duplicate_detected(self, mock_task):
        mock_task.delay.return_value = MagicMock(id="task-1")
        content = b"%PDF-1.4 duplicate-test"
        # Upload once
        self.client.post(
            self.URL,
            {"files": SimpleUploadedFile("r.pdf", content, content_type="application/pdf"),
             "job_role": "General"},
            format="multipart",
        )
        # Upload same file again
        response = self.client.post(
            self.URL,
            {"files": SimpleUploadedFile("r.pdf", content, content_type="application/pdf"),
             "job_role": "General"},
            format="multipart",
        )
        data = response.json()
        self.assertEqual(data["total_queued"], 0)
        self.assertEqual(len(data["duplicates"]), 1)
        self.assertEqual(data["duplicates"][0]["filename"], "r.pdf")

    @patch("resumes.tasks.parse_resume_task")
    def test_upload_invalid_extension_rejected(self, mock_task):
        exe_file = SimpleUploadedFile("virus.exe", b"MZ\x90\x00", content_type="application/octet-stream")
        response = self.client.post(
            self.URL,
            {"files": exe_file, "job_role": "General"},
            format="multipart",
        )
        # Rejected at serializer (400) or in loop (201 with errors) — either is valid
        self.assertIn(response.status_code, [400, 201])
        data = response.json()
        if response.status_code == 201:
            self.assertEqual(data["total_queued"], 0)
            self.assertGreater(len(data["errors"]), 0)

    @patch("resumes.tasks.parse_resume_task")
    def test_upload_php_file_rejected(self, mock_task):
        php_file = SimpleUploadedFile("shell.php", b"<?php system($_GET['cmd']); ?>",
                                      content_type="application/x-php")
        response = self.client.post(
            self.URL,
            {"files": php_file, "job_role": "General"},
            format="multipart",
        )
        self.assertIn(response.status_code, [400, 201])
        data = response.json()
        if response.status_code == 201:
            self.assertEqual(data["total_queued"], 0)
            self.assertGreater(len(data["errors"]), 0)

    @patch("resumes.tasks.parse_resume_task")
    def test_upload_oversized_file_rejected(self, mock_task):
        big_content = b"A" * (10 * 1024 * 1024 + 1)
        big_file = SimpleUploadedFile("big.pdf", big_content, content_type="application/pdf")
        response = self.client.post(
            self.URL,
            {"files": big_file, "job_role": "General"},
            format="multipart",
        )
        self.assertIn(response.status_code, [400, 201])
        data = response.json()
        if response.status_code == 201:
            self.assertEqual(data["total_queued"], 0)
            self.assertGreater(len(data["errors"]), 0)

    @patch("resumes.tasks.parse_resume_task")
    def test_upload_multiple_files(self, mock_task):
        mock_task.delay.return_value = MagicMock(id="task-x")
        files = [
            SimpleUploadedFile(f"resume{i}.pdf", f"%PDF-1.4 content{i}".encode(),
                               content_type="application/pdf")
            for i in range(3)
        ]
        response = self.client.post(
            self.URL,
            {"files": files, "job_role": "Engineering"},
            format="multipart",
        )
        data = response.json()
        self.assertEqual(data["total_queued"], 3)

    def test_upload_no_files_returns_error(self):
        response = self.client.post(self.URL, {"job_role": "General"}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("resumes.tasks.parse_resume_task")
    def test_path_traversal_in_filename_safe(self, mock_task):
        mock_task.delay.return_value = MagicMock(id="task-1")
        malicious = SimpleUploadedFile(
            "../../etc/passwd.pdf",
            b"%PDF-1.4 harmless",
            content_type="application/pdf",
        )
        response = self.client.post(
            self.URL,
            {"files": malicious, "job_role": "General"},
            format="multipart",
        )
        # Should succeed but filename should be sanitized
        if response.status_code == status.HTTP_201_CREATED:
            resume_id = response.json()["created"][0]
            resume = Resume.objects.get(id=resume_id)
            self.assertNotIn("..", resume.filename)

    @patch("resumes.tasks.parse_resume_task")
    def test_docx_upload_accepted(self, mock_task):
        mock_task.delay.return_value = MagicMock(id="task-1")
        response = self.client.post(
            self.URL,
            {"files": make_docx(), "job_role": "General"},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["total_queued"], 1)


# ---------------------------------------------------------------------------
# API — Stats endpoint
# ---------------------------------------------------------------------------

class ResumeStatsAPITest(APITestCase):
    URL = "/api/resumes/stats/"

    def setUp(self):
        Resume.objects.create(
            filename="a.pdf", file_type=".pdf", job_role="Backend",
            status="done", content_hash="hash1",
        )
        Resume.objects.create(
            filename="b.pdf", file_type=".pdf", job_role="Frontend",
            status="pending", content_hash="hash2",
        )
        Resume.objects.create(
            filename="c.pdf", file_type=".pdf", job_role="Backend",
            status="error", content_hash="hash3",
        )

    def test_stats_returns_correct_total(self):
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["total"], 3)

    def test_stats_by_status(self):
        data = self.client.get(self.URL).json()
        self.assertEqual(data["by_status"]["done"], 1)
        self.assertEqual(data["by_status"]["pending"], 1)
        self.assertEqual(data["by_status"]["error"], 1)

    def test_stats_by_role(self):
        data = self.client.get(self.URL).json()
        roles = {r["job_role"]: r["count"] for r in data["by_role"]}
        self.assertEqual(roles["Backend"], 2)
        self.assertEqual(roles["Frontend"], 1)


# ---------------------------------------------------------------------------
# API — List and filter
# ---------------------------------------------------------------------------

class ResumeListAPITest(APITestCase):
    URL = "/api/resumes/"

    def setUp(self):
        Resume.objects.create(
            filename="done.pdf", file_type=".pdf", job_role="Backend",
            status="done", content_hash="h1",
        )
        Resume.objects.create(
            filename="pending.pdf", file_type=".pdf", job_role="Frontend",
            status="pending", content_hash="h2",
        )

    def test_list_all(self):
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.json()["count"], 2)

    def test_filter_by_status(self):
        response = self.client.get(self.URL, {"status": "done"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()["results"]
        self.assertTrue(all(r["status"] == "done" for r in results))

    def test_filter_by_job_role(self):
        response = self.client.get(self.URL, {"job_role": "Backend"})
        results = response.json()["results"]
        self.assertTrue(all(r["job_role"] == "Backend" for r in results))


# ---------------------------------------------------------------------------
# API — Reparse endpoint
# ---------------------------------------------------------------------------

@override_settings(CELERY_TASK_ALWAYS_EAGER=False)
class ResumeReparseAPITest(APITestCase):
    def setUp(self):
        self.resume = Resume.objects.create(
            filename="err.pdf", file_type=".pdf", job_role="General",
            status="error", content_hash="errh1",
            error_message="Parsing failed",
        )

    @patch("resumes.tasks.parse_resume_task")
    def test_reparse_queues_task(self, mock_task):
        mock_task.delay.return_value = MagicMock(id="reparse-task")
        response = self.client.post(f"/api/resumes/{self.resume.id}/reparse/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.resume.refresh_from_db()
        self.assertEqual(self.resume.status, "pending")
        self.assertEqual(self.resume.error_message, "")
