import re as _re
from django.db import models

# Words that indicate the "name" field holds a role/title/platform instead of a person
_NAME_REJECT_WORDS = {
    # Section headers
    "technical", "skills", "experience", "education", "summary", "objective",
    "contact", "references", "certifications", "projects", "languages",
    "interests", "achievements", "awards", "publications",
    # Platforms / services
    "linkedin", "github", "portfolio", "profile", "website",
    # Job titles / seniority
    "engineer", "developer", "manager", "analyst", "designer", "architect",
    "consultant", "specialist", "lead", "senior", "junior", "intern",
    "director", "president", "vp", "cto", "ceo", "coo", "officer",
    "scientist", "researcher", "associate", "assistant", "coordinator",
    "administrator", "executive", "head", "principal", "staff",
    # Tech keywords that end up in names from badly parsed headers
    "python", "java", "javascript", "typescript", "react", "django",
    "full", "stack", "backend", "frontend", "software", "data",
    "ai", "ml", "devops", "cloud", "mobile", "web",
    # Generic filler
    "resume", "cv", "curriculum", "vitae", "updated", "final", "unknown",
}


def _validate_candidate_name(name: str) -> str:
    """Return name if it looks like a real person name, else empty string."""
    if not name:
        return ""
    name = name.strip().strip('"\'')
    if not name or name.upper() in ("UNKNOWN", "N/A", "NA", "-"):
        return ""
    words = name.split()
    if not (1 <= len(words) <= 4):
        return ""
    if any(ch.isdigit() for ch in name):
        return ""
    if any(w.lower() in _NAME_REJECT_WORDS for w in words):
        return ""
    if not words[0][0].isalpha():
        return ""
    if all(len(w) <= 1 for w in words):
        return ""
    # Normalise capitalisation: "AMAL" → "Amal", single initials stay uppercase
    def _fix(w: str) -> str:
        return w.upper() if len(w) == 1 else (w.capitalize() if w.isupper() else w)
    return " ".join(_fix(w) for w in words)


_FILENAME_STOP_WORDS = {
    # Job titles
    "engineer", "developer", "manager", "analyst", "designer", "architect",
    "consultant", "specialist", "lead", "senior", "junior", "intern",
    "director", "scientist", "researcher", "associate", "assistant",
    "coordinator", "administrator", "executive", "head", "principal",
    # Short role abbreviations & tech domains
    "dev", "eng", "ai", "ml", "ui", "ux", "qa", "ba",
    "backend", "frontend", "fullstack", "full", "stack",
    "software", "data", "web", "mobile", "cloud", "devops",
    # Generic filler
    "resume", "cv", "updated", "final", "new", "copy",
}


def _name_from_filename(filename: str) -> str:
    """Derive a display name from a resume filename when text extraction fails."""
    name = filename
    name = _re.sub(r"\.[^.]+$", "", name)                    # strip extension
    name = _re.sub(r"[\(\[]\s*\d+\s*[\)\]]", "", name)       # remove (1), [2]
    name = _re.sub(r"[_\-.]", " ", name)                      # underscores → spaces
    name = _re.sub(r"\s+", " ", name).strip()

    words = name.split()
    name_words: list[str] = []
    for w in words:
        if w.lower() in _FILENAME_STOP_WORDS:
            break  # stop at first role/filler word
        name_words.append(w)

    # Expand SHORT all-caps abbreviations (≤3 chars) as spaced initials: "AP" → "A P"
    # Longer all-caps words like "AMAL" are person names — just capitalise them.
    expanded: list[str] = []
    for w in name_words[:4]:
        if w.isupper() and 1 < len(w) <= 3:
            expanded.append(" ".join(list(w)))   # "AP" → "A P"
        elif w.isupper():
            expanded.append(w.capitalize())       # "AMAL" → "Amal"
        else:
            expanded.append(w[0].upper() + w[1:] if w else w)  # "john" → "John"

    return " ".join(expanded).strip()


class CandidateProfile(models.Model):
    resume = models.OneToOneField(
        "resumes.Resume", on_delete=models.CASCADE, related_name="candidate_profile"
    )
    structured_profile = models.JSONField(default=dict)
    embedding_vector = models.JSONField(default=list)  # stored as list[float]
    profile_text = models.TextField(blank=True)  # text used for embedding
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Recruiter feedback
    recruiter_notes = models.TextField(blank=True)
    is_shortlisted = models.BooleanField(default=False)

    # Bias flags
    bias_flags = models.JSONField(default=list)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Profile for Resume #{self.resume_id}"

    @property
    def candidate_name(self):
        contact = self.structured_profile.get("contact", {})
        if isinstance(contact, dict):
            raw = contact.get("name", "").strip()
            validated = _validate_candidate_name(raw)
            if validated:
                return validated
        # Derive from filename when AI extraction found nothing valid
        try:
            fn_name = _name_from_filename(self.resume.filename)
            if fn_name:
                return fn_name
        except Exception:
            pass
        return f"Candidate #{self.id}"

    @property
    def skills(self):
        return self.structured_profile.get("skills", [])

    @property
    def total_experience_years(self):
        exp = self.structured_profile.get("experience_years", {})
        if isinstance(exp, dict):
            return exp.get("total_years", 0)
        return exp or 0


class RecruiterFeedback(models.Model):
    """Track recruiter corrections to improve the system over time."""
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name="feedback")
    job = models.ForeignKey("jobs.Job", on_delete=models.CASCADE)
    action = models.CharField(
        max_length=30,
        choices=[
            ("shortlisted", "Shortlisted"),
            ("rejected", "Rejected"),
            ("interview", "Called for Interview"),
            ("hired", "Hired"),
        ],
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("candidate", "job")
        ordering = ["-created_at"]
