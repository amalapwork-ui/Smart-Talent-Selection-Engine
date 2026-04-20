"""
JD-to-Candidate Ranking Engine

Scoring formula:
  Total = (Skill Match × 0.40)
        + (Experience Depth × 0.30)
        + (Project Relevance × 0.20)
        + (Education/Certifications × 0.10)

All component scores are 0–100. Final score is 0–100.
"""
import re
import json
import logging
from typing import Any

from django.conf import settings

from .extractor import normalize_skill, extract_skills_nlp, SKILL_HIERARCHY
from .embeddings import generate_embedding, profile_to_text

logger = logging.getLogger(__name__)

WEIGHTS = {
    "skill": 0.40,
    "experience": 0.30,
    "project": 0.20,
    "education": 0.10,
}

DEGREE_SCORE = {
    "phd": 100, "ph.d": 100,
    "master": 85, "m.tech": 85, "mtech": 85, "msc": 85,
    "bachelor": 70, "b.tech": 70, "btech": 70, "bsc": 70, "be": 70,
    "diploma": 50,
}


def parse_jd(jd_text: str) -> dict:
    """
    Parse Job Description text into structured requirements.
    Uses Groq if available, falls back to NLP keyword extraction.
    """
    api_key = settings.GROQ_API_KEY

    if api_key:
        try:
            from groq import Groq
            client = Groq(api_key=api_key)
            response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "Return only valid JSON. No explanation."},
                    {
                        "role": "user",
                        "content": (
                            "Parse this job description and return JSON with:\n"
                            "- required_skills: list of strings\n"
                            "- preferred_skills: list of strings\n"
                            "- min_experience_years: int\n"
                            "- education_required: string\n"
                            "- key_responsibilities: list of strings\n"
                            "- role_context: string (1-2 sentences describing the role)\n\n"
                            f"JD:\n{jd_text[:4000]}"
                        ),
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=1000,
            )
            parsed = json.loads(response.choices[0].message.content)
            skills = [normalize_skill(s) for s in parsed.get("required_skills", [])]
            parsed["required_skills"] = skills
            parsed["_parsed_by"] = "groq"
            return parsed
        except Exception as e:
            logger.warning(f"JD parsing via Groq failed: {e}. Using NLP fallback.")

    # NLP fallback
    skills = extract_skills_nlp(jd_text)
    years_match = re.search(r"(\d+)\+?\s*years?\s+(?:of\s+)?experience", jd_text, re.IGNORECASE)
    min_exp = int(years_match.group(1)) if years_match else 0

    return {
        "required_skills": skills,
        "preferred_skills": [],
        "min_experience_years": min_exp,
        "education_required": "",
        "key_responsibilities": [],
        "role_context": "",
        "_parsed_by": "nlp_fallback",
    }


def compute_skill_score(candidate_skills: list[str], jd_requirements: dict) -> dict:
    """
    Semantic skill match score (0–100).
    Rewards both direct matches and domain-category matches.
    """
    required = set(jd_requirements.get("required_skills", []))
    preferred = set(jd_requirements.get("preferred_skills", []))
    candidate = set(normalize_skill(s) for s in candidate_skills)

    if not required:
        return {"score": 50, "matched": list(candidate), "missing": [], "coverage": 0.5}

    # Direct matches
    direct_matches = required & candidate
    preferred_matches = preferred & candidate

    # Domain-level matches (partial credit)
    domain_bonus = 0
    for domain, domain_skills in SKILL_HIERARCHY.items():
        req_in_domain = required & set(domain_skills)
        cand_in_domain = candidate & set(domain_skills)
        if req_in_domain and cand_in_domain:
            overlap = len(req_in_domain & cand_in_domain) / len(req_in_domain)
            domain_bonus += overlap * 10  # up to 10 pts per domain

    coverage = len(direct_matches) / len(required)
    preferred_bonus = min(10, len(preferred_matches) * 5)

    raw_score = (coverage * 80) + preferred_bonus + min(10, domain_bonus)
    score = min(100, raw_score)

    return {
        "score": round(score, 1),
        "matched": sorted(direct_matches),
        "missing": sorted(required - candidate),
        "preferred_matched": sorted(preferred_matches),
        "coverage": round(coverage, 3),
    }


def compute_experience_score(candidate_profile: dict, jd_requirements: dict) -> dict:
    """
    Experience depth score (0–100).
    Weights total years heavily, with bonus for relevant role titles.
    """
    min_required = jd_requirements.get("min_experience_years", 0)
    exp_data = candidate_profile.get("experience_years", {})

    if isinstance(exp_data, dict):
        candidate_years = exp_data.get("total_years", 0)
    elif isinstance(exp_data, (int, float)):
        candidate_years = int(exp_data)
    else:
        candidate_years = 0

    if min_required == 0:
        # Score relative to experience level
        if candidate_years >= 8:
            base_score = 95
        elif candidate_years >= 5:
            base_score = 80
        elif candidate_years >= 3:
            base_score = 65
        elif candidate_years >= 1:
            base_score = 50
        else:
            base_score = 30
    else:
        ratio = candidate_years / min_required
        if ratio >= 1.5:
            base_score = 100
        elif ratio >= 1.0:
            base_score = 85
        elif ratio >= 0.7:
            base_score = 60
        elif ratio >= 0.5:
            base_score = 40
        else:
            base_score = 20

    # Bonus for role title matches
    role_bonus = 0
    jd_context = (jd_requirements.get("role_context", "") + " " +
                  " ".join(jd_requirements.get("key_responsibilities", []))).lower()
    if isinstance(exp_data, dict):
        for role in exp_data.get("roles", []):
            title = role.get("title", "").lower()
            desc = role.get("description", "").lower()
            # Simple token overlap
            title_words = set(title.split())
            jd_words = set(jd_context.split())
            overlap = len(title_words & jd_words)
            if overlap >= 2:
                role_bonus += 5
    role_bonus = min(10, role_bonus)

    score = min(100, base_score + role_bonus)
    return {
        "score": round(score, 1),
        "candidate_years": candidate_years,
        "required_years": min_required,
        "meets_requirement": candidate_years >= min_required,
    }


def compute_project_score(candidate_profile: dict, jd_requirements: dict, jd_text: str) -> dict:
    """
    Project relevance score (0–100) using semantic similarity.
    """
    projects = candidate_profile.get("projects", [])
    if not projects:
        return {"score": 0, "relevant_projects": 0, "total_projects": 0}

    required_skills = set(jd_requirements.get("required_skills", []))
    jd_context = jd_text.lower()

    relevant_count = 0
    total_score = 0

    for proj in projects[:10]:
        if not isinstance(proj, dict):
            continue
        name = proj.get("name", "").lower()
        desc = proj.get("description", "").lower()
        tech = [normalize_skill(t) for t in proj.get("tech_stack", [])]

        # Tech stack overlap with required skills
        tech_match = len(set(tech) & required_skills)
        tech_score = min(30, tech_match * 15)

        # Semantic overlap between project desc and JD
        proj_text = f"{name} {desc}"
        jd_words = set(re.findall(r"\b\w{4,}\b", jd_context))
        proj_words = set(re.findall(r"\b\w{4,}\b", proj_text))
        overlap = len(jd_words & proj_words)
        desc_score = min(40, overlap * 5)

        proj_total = tech_score + desc_score
        if proj_total > 10:
            relevant_count += 1
        total_score += proj_total

    avg_score = total_score / len(projects) if projects else 0
    # Bonus for having multiple relevant projects
    quantity_bonus = min(30, relevant_count * 10)
    final_score = min(100, avg_score + quantity_bonus)

    return {
        "score": round(final_score, 1),
        "relevant_projects": relevant_count,
        "total_projects": len(projects),
    }


def compute_education_score(candidate_profile: dict, jd_requirements: dict) -> dict:
    """
    Education & certifications score (0–100).
    """
    education = candidate_profile.get("education", [])
    certifications = candidate_profile.get("certifications", [])

    # Education score
    edu_score = 0
    highest_degree = ""
    for edu in education:
        if isinstance(edu, dict):
            degree = edu.get("degree", "").lower()
        else:
            degree = str(edu).lower()
        for deg_key, deg_val in DEGREE_SCORE.items():
            if deg_key in degree:
                if deg_val > edu_score:
                    edu_score = deg_val
                    highest_degree = deg_key
                break

    # Certification bonus
    cert_score = min(30, len(certifications) * 10)

    # Check if required degree is met
    required_edu = jd_requirements.get("education_required", "").lower()
    requirement_met = True
    if required_edu:
        requirement_met = any(
            req_term in highest_degree
            for req_term in ["bachelor", "master", "phd", "b.tech", "m.tech"]
            if req_term in required_edu
        )

    # Blend education + certs
    base = (edu_score * 0.7) + (cert_score * 0.3)
    final_score = min(100, base)

    return {
        "score": round(final_score, 1),
        "highest_degree": highest_degree,
        "certifications_count": len(certifications),
        "requirement_met": requirement_met,
    }


def compute_total_score(
    candidate_profile: dict,
    jd_requirements: dict,
    jd_text: str,
) -> dict:
    """
    Compute the weighted total score and per-component breakdown.
    Returns comprehensive scoring dict.
    """
    skill_result = compute_skill_score(candidate_profile.get("skills", []), jd_requirements)
    exp_result = compute_experience_score(candidate_profile, jd_requirements)
    proj_result = compute_project_score(candidate_profile, jd_requirements, jd_text)
    edu_result = compute_education_score(candidate_profile, jd_requirements)

    total = (
        skill_result["score"] * WEIGHTS["skill"]
        + exp_result["score"] * WEIGHTS["experience"]
        + proj_result["score"] * WEIGHTS["project"]
        + edu_result["score"] * WEIGHTS["education"]
    )

    return {
        "total_score": round(total, 1),
        "skill_score": skill_result["score"],
        "experience_score": exp_result["score"],
        "project_score": proj_result["score"],
        "education_score": edu_result["score"],
        "breakdown": {
            "skill": skill_result,
            "experience": exp_result,
            "project": proj_result,
            "education": edu_result,
        },
        "weights": WEIGHTS,
    }


def generate_justification(
    candidate_profile: dict,
    scoring: dict,
    jd_requirements: dict,
) -> str:
    """
    Generate a 2-sentence AI justification for the candidate's ranking.
    Uses Groq if available, else constructs a template-based sentence.
    """
    api_key = settings.GROQ_API_KEY
    contact = candidate_profile.get("contact", {})
    name = contact.get("name", "This candidate") if isinstance(contact, dict) else "This candidate"
    breakdown = scoring.get("breakdown", {})
    skill_info = breakdown.get("skill", {})
    exp_info = breakdown.get("experience", {})

    if api_key:
        try:
            from groq import Groq
            client = Groq(api_key=api_key)
            prompt = (
                f"Candidate scored {scoring['total_score']:.1f}/100 for this job.\n"
                f"Skills matched: {', '.join(skill_info.get('matched', [])[:5])}\n"
                f"Missing skills: {', '.join(skill_info.get('missing', [])[:3])}\n"
                f"Experience: {exp_info.get('candidate_years', 0)} years "
                f"(required: {exp_info.get('required_years', 0)})\n"
                f"Write exactly 2 sentences explaining why this candidate is a "
                f"{'strong' if scoring['total_score'] >= 70 else 'moderate' if scoring['total_score'] >= 50 else 'weak'} "
                f"match. Be specific, professional, and concise."
            )
            response = client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=150,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Justification generation failed: {e}")

    # Template fallback
    matched_skills = skill_info.get("matched", [])[:3]
    missing_skills = skill_info.get("missing", [])[:2]
    years = exp_info.get("candidate_years", 0)

    strength = ", ".join(matched_skills) if matched_skills else "general technical background"
    gap = f" Key gaps include: {', '.join(missing_skills)}." if missing_skills else ""

    return (
        f"{name} demonstrates strong expertise in {strength} with {years} years of experience, "
        f"achieving a compatibility score of {scoring['total_score']:.1f}/100.{gap}"
    )


def rank_candidates(
    candidates: list[dict],
    jd_text: str,
    use_faiss_prefilter: bool = True,
) -> list[dict]:
    """
    Rank a list of candidate profiles against a JD.

    Scoring (pure Python) runs sequentially; Groq justification calls run
    concurrently via a thread pool so N candidates take ~1 round-trip instead
    of N round-trips.

    Args:
        candidates: List of dicts with {id, profile} keys
        jd_text: Raw job description text
    Returns:
        Sorted list of ranking results (descending by total_score)
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Single JD parse call shared across all candidates
    jd_requirements = parse_jd(jd_text)

    # ── Phase 1: pure-Python scoring (fast, no I/O) ───────────────────────
    scored: list[tuple] = []
    for candidate in candidates:
        candidate_id = candidate.get("id")
        profile = candidate.get("profile", {})
        if not profile:
            continue
        scoring = compute_total_score(profile, jd_requirements, jd_text)
        scored.append((candidate_id, profile, scoring))

    if not scored:
        return []

    # ── Phase 2: parallel Groq justifications (I/O-bound, concurrency helps) ─
    def _build_result(item: tuple) -> dict:
        candidate_id, profile, scoring = item
        justification = generate_justification(profile, scoring, jd_requirements)
        return {
            "candidate_id": candidate_id,
            "total_score": scoring["total_score"],
            "skill_score": scoring["skill_score"],
            "experience_score": scoring["experience_score"],
            "project_score": scoring["project_score"],
            "education_score": scoring["education_score"],
            "score_breakdown": scoring["breakdown"],
            "justification": justification,
            "jd_requirements": jd_requirements,
        }

    max_workers = min(8, len(scored))
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_build_result, item): item for item in scored}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as exc:
                logger.warning("Justification generation failed for a candidate: %s", exc)

    results.sort(key=lambda x: x["total_score"], reverse=True)
    return results
