"""
Unit tests for ai_pipeline — extractor and ranker pure logic.
These tests do NOT require the database or Celery.
"""
from django.test import TestCase

from ai_pipeline.extractor import (
    extract_skills_regex,
    normalize_skill,
    extract_experience_regex,
    extract_education_regex,
)
from ai_pipeline.ranker import (
    compute_skill_score,
    compute_experience_score,
    compute_project_score,
    compute_education_score,
    compute_total_score,
    rank_candidates,
)


# ---------------------------------------------------------------------------
# Extractor tests
# ---------------------------------------------------------------------------

class NormalizeSkillTest(TestCase):
    def test_canonical_name_unchanged(self):
        self.assertEqual(normalize_skill("python"), "python")

    def test_synonym_resolved(self):
        # "js" should resolve to "javascript"
        result = normalize_skill("js")
        self.assertEqual(result, "javascript")

    def test_uppercase_lowercased(self):
        result = normalize_skill("Python")
        self.assertEqual(result, "python")

    def test_unknown_skill_lowercased(self):
        result = normalize_skill("XYZFramework")
        self.assertEqual(result, "xyzframework")

    def test_react_js_resolves(self):
        result = normalize_skill("reactjs")
        self.assertIn(result, ["react", "reactjs"])

    def test_empty_string(self):
        result = normalize_skill("")
        self.assertEqual(result, "")


class ExtractSkillsRegexTest(TestCase):
    RESUME_TEXT = """
    Skills: Python, Django, React, PostgreSQL, Docker, AWS
    Also experienced with REST APIs and Git version control.
    """

    def test_extracts_known_skills(self):
        skills = extract_skills_regex(self.RESUME_TEXT)
        self.assertIn("python", skills)
        self.assertIn("django", skills)
        self.assertIn("react", skills)

    def test_no_false_positives_from_noise(self):
        skills = extract_skills_regex("Lorem ipsum dolor sit amet consectetur")
        self.assertEqual(skills, [])

    def test_case_insensitive(self):
        skills = extract_skills_regex("PYTHON and REACT")
        self.assertIn("python", skills)
        self.assertIn("react", skills)

    def test_empty_text(self):
        skills = extract_skills_regex("")
        self.assertEqual(skills, [])

    def test_deduplication(self):
        skills = extract_skills_regex("Python python PYTHON")
        python_count = skills.count("python")
        self.assertEqual(python_count, 1)


class ExtractExperienceTest(TestCase):
    def test_extracts_year_statement(self):
        text = "I have 5 years of experience in software development."
        result = extract_experience_regex(text)
        self.assertIsInstance(result, dict)
        total = result.get("total_years", 0)
        self.assertGreaterEqual(total, 4)

    def test_no_experience_mentioned(self):
        text = "Fresh graduate looking for opportunities."
        result = extract_experience_regex(text)
        self.assertIsInstance(result, dict)
        self.assertGreaterEqual(result.get("total_years", 0), 0)

    def test_empty_text(self):
        result = extract_experience_regex("")
        self.assertIsInstance(result, dict)


class ExtractEducationTest(TestCase):
    def test_btech_detected(self):
        text = "B.Tech in Computer Science from IIT Delhi, 2019"
        result = extract_education_regex(text)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)

    def test_phd_detected(self):
        text = "Ph.D in Machine Learning from IISc Bangalore"
        result = extract_education_regex(text)
        self.assertTrue(len(result) > 0)

    def test_no_education_text(self):
        text = "Skilled in Python and JavaScript with 3 years experience."
        result = extract_education_regex(text)
        self.assertIsInstance(result, list)


# ---------------------------------------------------------------------------
# Ranker — compute_skill_score
# ---------------------------------------------------------------------------

class ComputeSkillScoreTest(TestCase):
    def _jd(self, required=None, preferred=None):
        return {
            "required_skills": required or [],
            "preferred_skills": preferred or [],
        }

    def test_perfect_match_scores_high(self):
        # Use skills with no synonyms to avoid normalization surprises
        candidate_skills = ["python", "django", "react", "docker"]
        jd = self._jd(required=["python", "django", "react", "docker"])
        result = compute_skill_score(candidate_skills, jd)
        # 100% coverage → base 80 pts; domain bonuses may push higher.
        self.assertGreaterEqual(result["score"], 65)
        self.assertEqual(set(result["matched"]), {"python", "django", "react", "docker"})
        self.assertEqual(result["missing"], [])

    def test_no_match_scores_low(self):
        candidate_skills = ["cobol", "fortran", "pascal"]
        jd = self._jd(required=["python", "django", "react"])
        result = compute_skill_score(candidate_skills, jd)
        self.assertLessEqual(result["score"], 20)
        self.assertEqual(result["matched"], [])

    def test_partial_match(self):
        candidate_skills = ["python", "flask"]
        jd = self._jd(required=["python", "django", "postgresql", "docker"])
        result = compute_skill_score(candidate_skills, jd)
        self.assertGreater(result["score"], 0)
        self.assertLess(result["score"], 80)
        self.assertIn("python", result["matched"])

    def test_empty_required_skills_returns_50(self):
        result = compute_skill_score(["python", "react"], self._jd(required=[]))
        self.assertEqual(result["score"], 50)

    def test_preferred_skills_add_bonus(self):
        candidate_skills = ["python", "django", "redis"]
        jd_no_pref = self._jd(required=["python", "django"])
        jd_with_pref = self._jd(required=["python", "django"], preferred=["redis"])
        score_no_pref = compute_skill_score(candidate_skills, jd_no_pref)["score"]
        score_with_pref = compute_skill_score(candidate_skills, jd_with_pref)["score"]
        self.assertGreaterEqual(score_with_pref, score_no_pref)

    def test_score_bounded_0_100(self):
        skills = ["python"] * 100
        jd = self._jd(required=["python"], preferred=["python"] * 20)
        result = compute_skill_score(skills, jd)
        self.assertGreaterEqual(result["score"], 0)
        self.assertLessEqual(result["score"], 100)

    def test_missing_skills_populated(self):
        candidate_skills = ["python"]
        jd = self._jd(required=["python", "django", "react"])
        result = compute_skill_score(candidate_skills, jd)
        self.assertIn("django", result["missing"])
        self.assertIn("react", result["missing"])


# ---------------------------------------------------------------------------
# Ranker — compute_experience_score
# ---------------------------------------------------------------------------

class ComputeExperienceScoreTest(TestCase):
    def _profile(self, years):
        return {"experience_years": {"total_years": years, "roles": [], "timeline": []}}

    def _jd(self, min_years=0):
        return {"min_experience_years": min_years, "role_context": "", "key_responsibilities": []}

    def test_meets_requirement_scores_high(self):
        result = compute_experience_score(self._profile(5), self._jd(min_years=3))
        self.assertGreaterEqual(result["score"], 80)
        self.assertTrue(result["meets_requirement"])

    def test_exceeds_requirement(self):
        result = compute_experience_score(self._profile(10), self._jd(min_years=3))
        self.assertGreaterEqual(result["score"], 90)

    def test_below_requirement_scores_low(self):
        result = compute_experience_score(self._profile(1), self._jd(min_years=5))
        self.assertLessEqual(result["score"], 50)
        self.assertFalse(result["meets_requirement"])

    def test_zero_experience_no_requirement(self):
        result = compute_experience_score(self._profile(0), self._jd(min_years=0))
        self.assertGreater(result["score"], 0)
        self.assertLessEqual(result["score"], 100)

    def test_senior_no_requirement(self):
        result = compute_experience_score(self._profile(8), self._jd(min_years=0))
        self.assertGreaterEqual(result["score"], 80)

    def test_experience_as_int_still_works(self):
        profile = {"experience_years": 4}
        result = compute_experience_score(profile, self._jd(min_years=3))
        self.assertGreaterEqual(result["score"], 70)

    def test_score_bounded(self):
        result = compute_experience_score(self._profile(100), self._jd(min_years=1))
        self.assertLessEqual(result["score"], 100)
        self.assertGreaterEqual(result["score"], 0)


# ---------------------------------------------------------------------------
# Ranker — compute_education_score
# ---------------------------------------------------------------------------

class ComputeEducationScoreTest(TestCase):
    def test_phd_scores_highest(self):
        profile = {"education": [{"degree": "Ph.D Machine Learning"}], "certifications": []}
        result = compute_education_score(profile, {})
        self.assertGreaterEqual(result["score"], 65)

    def test_masters_scores_higher_than_bachelor(self):
        prof_master = {"education": [{"degree": "M.Tech CS"}], "certifications": []}
        prof_bachelor = {"education": [{"degree": "B.Tech CS"}], "certifications": []}
        score_master = compute_education_score(prof_master, {})["score"]
        score_bachelor = compute_education_score(prof_bachelor, {})["score"]
        self.assertGreater(score_master, score_bachelor)

    def test_certifications_add_bonus(self):
        prof_no_cert = {
            "education": [{"degree": "B.Tech CS"}],
            "certifications": [],
        }
        prof_with_cert = {
            "education": [{"degree": "B.Tech CS"}],
            "certifications": ["AWS", "Docker"],
        }
        score_no = compute_education_score(prof_no_cert, {})["score"]
        score_yes = compute_education_score(prof_with_cert, {})["score"]
        self.assertGreater(score_yes, score_no)

    def test_no_education_zero_certs(self):
        profile = {"education": [], "certifications": []}
        result = compute_education_score(profile, {})
        self.assertEqual(result["score"], 0)

    def test_score_bounded(self):
        profile = {
            "education": [{"degree": "Ph.D"}, {"degree": "Master"}, {"degree": "Bachelor"}],
            "certifications": ["A", "B", "C", "D", "E"],
        }
        result = compute_education_score(profile, {})
        self.assertLessEqual(result["score"], 100)


# ---------------------------------------------------------------------------
# Ranker — compute_project_score
# ---------------------------------------------------------------------------

class ComputeProjectScoreTest(TestCase):
    JD_REQS = {"required_skills": ["react", "python", "postgresql"]}
    JD_TEXT = "We need React and Python backend with PostgreSQL database experience"

    def test_no_projects_returns_zero(self):
        profile = {"projects": []}
        result = compute_project_score(profile, self.JD_REQS, self.JD_TEXT)
        self.assertEqual(result["score"], 0)
        self.assertEqual(result["total_projects"], 0)

    def test_relevant_project_scores_higher(self):
        profile_relevant = {
            "projects": [{
                "name": "React Dashboard",
                "description": "React frontend with Python backend and PostgreSQL",
                "tech_stack": ["react", "python", "postgresql"],
            }]
        }
        profile_irrelevant = {
            "projects": [{
                "name": "Java App",
                "description": "Java enterprise application",
                "tech_stack": ["java", "spring", "oracle"],
            }]
        }
        score_rel = compute_project_score(profile_relevant, self.JD_REQS, self.JD_TEXT)["score"]
        score_irr = compute_project_score(profile_irrelevant, self.JD_REQS, self.JD_TEXT)["score"]
        self.assertGreater(score_rel, score_irr)

    def test_multiple_relevant_projects_bonus(self):
        profile_one = {
            "projects": [
                {"name": "App", "description": "Python React app", "tech_stack": ["react", "python"]}
            ]
        }
        profile_many = {
            "projects": [
                {"name": "App1", "description": "Python React app", "tech_stack": ["react", "python"]},
                {"name": "App2", "description": "Python PostgreSQL service", "tech_stack": ["python", "postgresql"]},
                {"name": "App3", "description": "React frontend", "tech_stack": ["react"]},
            ]
        }
        score_one = compute_project_score(profile_one, self.JD_REQS, self.JD_TEXT)["score"]
        score_many = compute_project_score(profile_many, self.JD_REQS, self.JD_TEXT)["score"]
        self.assertGreaterEqual(score_many, score_one)


# ---------------------------------------------------------------------------
# Ranker — compute_total_score and rank_candidates
# ---------------------------------------------------------------------------

class ComputeTotalScoreTest(TestCase):
    STRONG_PROFILE = {
        "skills": ["python", "django", "postgresql", "docker", "rest api"],
        "experience_years": {"total_years": 4, "roles": [], "timeline": []},
        "projects": [
            {
                "name": "Backend API",
                "description": "Django REST API with PostgreSQL and Docker deployment",
                "tech_stack": ["python", "django", "postgresql", "docker"],
            }
        ],
        "education": [{"degree": "B.Tech Computer Science"}],
        "certifications": ["AWS Certified"],
    }

    WEAK_PROFILE = {
        "skills": ["html", "css"],
        "experience_years": {"total_years": 0, "roles": [], "timeline": []},
        "projects": [],
        "education": [],
        "certifications": [],
    }

    JD_REQS = {
        "required_skills": ["python", "django", "postgresql", "docker"],
        "preferred_skills": [],
        "min_experience_years": 2,
        "education_required": "",
    }
    JD_TEXT = "Python Django backend developer with PostgreSQL and Docker experience"

    def test_strong_profile_scores_high(self):
        result = compute_total_score(self.STRONG_PROFILE, self.JD_REQS, self.JD_TEXT)
        self.assertGreaterEqual(result["total_score"], 60)

    def test_weak_profile_scores_low(self):
        result = compute_total_score(self.WEAK_PROFILE, self.JD_REQS, self.JD_TEXT)
        self.assertLessEqual(result["total_score"], 40)

    def test_total_score_is_weighted_average(self):
        result = compute_total_score(self.STRONG_PROFILE, self.JD_REQS, self.JD_TEXT)
        expected = (
            result["skill_score"] * 0.40
            + result["experience_score"] * 0.30
            + result["project_score"] * 0.20
            + result["education_score"] * 0.10
        )
        self.assertAlmostEqual(result["total_score"], round(expected, 1), places=0)

    def test_scores_bounded_0_100(self):
        result = compute_total_score(self.STRONG_PROFILE, self.JD_REQS, self.JD_TEXT)
        for key in ("total_score", "skill_score", "experience_score", "project_score", "education_score"):
            self.assertGreaterEqual(result[key], 0)
            self.assertLessEqual(result[key], 100)

    def test_breakdown_keys_present(self):
        result = compute_total_score(self.STRONG_PROFILE, self.JD_REQS, self.JD_TEXT)
        self.assertIn("breakdown", result)
        for k in ("skill", "experience", "project", "education"):
            self.assertIn(k, result["breakdown"])


class RankCandidatesTest(TestCase):
    STRONG = {
        "id": 1,
        "profile": {
            "skills": ["python", "django", "react", "postgresql"],
            "experience_years": {"total_years": 5, "roles": [], "timeline": []},
            "projects": [{"name": "P", "description": "Django React app", "tech_stack": ["python", "react"]}],
            "education": [{"degree": "B.Tech CS"}],
            "certifications": ["AWS"],
            "contact": {"name": "Alice"},
        },
    }
    WEAK = {
        "id": 2,
        "profile": {
            "skills": ["cobol"],
            "experience_years": {"total_years": 0, "roles": [], "timeline": []},
            "projects": [],
            "education": [],
            "certifications": [],
            "contact": {"name": "Bob"},
        },
    }
    JD = "We need a Python Django developer with React frontend skills and 3+ years experience."

    def test_sorted_descending(self):
        results = rank_candidates([self.WEAK, self.STRONG], self.JD)
        self.assertGreaterEqual(results[0]["total_score"], results[-1]["total_score"])

    def test_strong_ranked_above_weak(self):
        results = rank_candidates([self.WEAK, self.STRONG], self.JD)
        strong_result = next(r for r in results if r["candidate_id"] == 1)
        weak_result = next(r for r in results if r["candidate_id"] == 2)
        self.assertGreater(strong_result["total_score"], weak_result["total_score"])

    def test_empty_candidates(self):
        results = rank_candidates([], self.JD)
        self.assertEqual(results, [])

    def test_result_keys_present(self):
        results = rank_candidates([self.STRONG], self.JD)
        self.assertEqual(len(results), 1)
        r = results[0]
        for key in ("candidate_id", "total_score", "skill_score", "experience_score",
                    "project_score", "education_score", "score_breakdown", "justification"):
            self.assertIn(key, r)

    def test_empty_profile_skipped(self):
        candidates = [self.STRONG, {"id": 99, "profile": {}}]
        results = rank_candidates(candidates, self.JD)
        ids = [r["candidate_id"] for r in results]
        # Empty profile should either be skipped or score very low
        if 99 in ids:
            empty_result = next(r for r in results if r["candidate_id"] == 99)
            self.assertLessEqual(empty_result["total_score"], 30)

    def test_justification_non_empty(self):
        results = rank_candidates([self.STRONG], self.JD)
        self.assertTrue(len(results[0]["justification"]) > 0)
