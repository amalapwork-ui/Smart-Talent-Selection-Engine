"""
Semantic Profile & Intent Mapper  —  spaCy-free, Python 3.13 safe

Extraction pipeline (three layers, each adds coverage):

  Layer 1 · Regex + keyword ontology  (always runs, zero dependencies)
  Layer 2 · NLTK enrichment           (runs if nltk is installed)
  Layer 3 · Groq LLM structuring      (runs when GROQ_API_KEY is set)

Layers 2 and 3 supplement — never replace — layer 1.
Final profile is the union / merge of all three layers.
"""

from __future__ import annotations

import os
import re
import json
import string
import logging
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)

# ── NLTK bootstrap (graceful — never crashes on missing data) ─────────────

def _bootstrap_nltk() -> bool:
    """Download required NLTK corpora on first run. Returns True if ready."""
    try:
        import nltk  # noqa: F401
        for pkg in ("punkt", "punkt_tab", "averaged_perceptron_tagger",
                    "averaged_perceptron_tagger_eng", "stopwords", "wordnet"):
            try:
                nltk.data.find(f"tokenizers/{pkg}" if "punkt" in pkg
                               else f"corpora/{pkg}" if pkg in ("stopwords", "wordnet")
                               else f"taggers/{pkg}")
            except LookupError:
                nltk.download(pkg, quiet=True)
        return True
    except Exception as e:
        logger.warning(f"NLTK init failed (non-fatal): {e}")
        return False

_NLTK_READY = _bootstrap_nltk()


# ═══════════════════════════════════════════════════════════════════════════
#  ONTOLOGY  —  skill synonyms + domain hierarchy
# ═══════════════════════════════════════════════════════════════════════════

SKILL_SYNONYMS: dict[str, list[str]] = {
    # ── Languages ──────────────────────────────────────────────────────────
    "python":           ["python3", "py", "python programming", "python2"],
    "javascript":       ["js", "es6", "es2015", "es2017", "ecmascript", "vanilla js"],
    "typescript":       ["ts", "tsx"],
    "java":             ["core java", "java8", "java 8", "java 11", "java17", "java 17",
                         "jvm", "j2ee", "java ee"],
    "c++":              ["cpp", "c plus plus", "c/c++"],
    "c#":               ["csharp", "c sharp", ".net c#", "dotnet"],
    "ruby":             ["ruby on rails", "ror"],
    "go":               ["golang"],
    "rust":             ["rust lang"],
    "php":              ["php7", "php8", "laravel", "symfony"],
    "swift":            ["swiftui"],
    "kotlin":           [],
    "scala":            ["akka"],
    "r":                ["r programming", "r language"],
    "matlab":           [],
    "bash":             ["shell scripting", "shell script", "bash scripting", "sh", "zsh"],
    # ── Frontend ───────────────────────────────────────────────────────────
    "react":            ["react.js", "reactjs", "react native", "react hooks",
                         "react redux", "next.js", "nextjs"],
    "vue":              ["vue.js", "vuejs", "nuxt.js", "nuxtjs"],
    "angular":          ["angularjs", "angular 2", "angular cli"],
    "html":             ["html5", "html/css"],
    "css":              ["css3", "css grid", "flexbox", "sass", "scss", "less",
                         "tailwind", "tailwindcss", "bootstrap", "material ui",
                         "mui", "styled components"],
    "svelte":           [],
    "redux":            ["vuex", "zustand", "mobx", "state management"],
    # ── Backend frameworks ─────────────────────────────────────────────────
    "django":           ["django rest framework", "drf", "django orm"],
    "flask":            ["flask-restful"],
    "fastapi":          ["starlette"],
    "node.js":          ["nodejs", "node", "express.js", "expressjs", "express",
                         "nestjs", "nest.js"],
    "spring":           ["spring boot", "spring mvc", "spring framework"],
    "asp.net":          ["asp.net core", "asp.net mvc", ".net core"],
    # ── Databases ──────────────────────────────────────────────────────────
    "sql":              ["mysql", "postgresql", "postgres", "sqlite", "tsql", "plsql",
                         "oracle db", "sql server", "mssql", "relational database",
                         "mariadb"],
    "mongodb":          ["mongo", "mongoose", "nosql", "document database"],
    "redis":            ["redis cache", "caching"],
    "elasticsearch":    ["elastic", "elk stack", "kibana", "logstash"],
    "cassandra":        ["apache cassandra"],
    "dynamodb":         ["amazon dynamodb"],
    "firebase":         ["firestore", "realtime database"],
    "neo4j":            ["graph database"],
    # ── Cloud & DevOps ─────────────────────────────────────────────────────
    "aws":              ["amazon web services", "ec2", "s3", "lambda", "rds",
                         "ecs", "eks", "cloudformation", "aws cloud", "cloud"],
    "azure":            ["microsoft azure", "azure devops", "azure functions"],
    "gcp":              ["google cloud", "google cloud platform", "gke",
                         "bigquery", "cloud run"],
    "docker":           ["containerization", "containers", "dockerfile"],
    "kubernetes":       ["k8s", "container orchestration", "helm", "kubectl"],
    "terraform":        ["infrastructure as code", "iac"],
    "ansible":          ["configuration management"],
    "jenkins":          ["ci/cd", "continuous integration", "continuous deployment",
                         "github actions", "gitlab ci", "circleci", "travis ci",
                         "devops pipeline"],
    "linux":            ["unix", "ubuntu", "centos", "rhel", "debian"],
    # ── Version control ────────────────────────────────────────────────────
    "git":              ["github", "gitlab", "bitbucket", "version control", "vcs"],
    # ── REST & APIs ────────────────────────────────────────────────────────
    "rest api":         ["restful", "rest", "api development", "web api", "api design",
                         "http api", "json api", "backend api"],
    "graphql":          ["apollo"],
    "grpc":             ["protocol buffers", "protobuf"],
    "websocket":        ["ws", "socket.io", "real-time"],
    "microservices":    ["service mesh", "istio", "api gateway"],
    # ── ML / AI ────────────────────────────────────────────────────────────
    "machine learning": ["ml", "deep learning", "dl", "artificial intelligence",
                         "ai", "neural networks", "supervised learning",
                         "unsupervised learning", "reinforcement learning"],
    "tensorflow":       ["tf", "keras", "tf2"],
    "pytorch":          ["torch", "libtorch"],
    "scikit-learn":     ["sklearn", "sci-kit learn"],
    "nlp":              ["natural language processing", "text mining", "text analytics",
                         "named entity recognition", "ner", "sentiment analysis",
                         "transformers", "bert", "gpt", "llm", "large language model",
                         "langchain", "llamaindex"],
    "computer vision":  ["cv", "image processing", "opencv", "object detection",
                         "yolo", "image recognition"],
    "data analysis":    ["data analytics", "data science", "data engineering",
                         "data pipeline", "etl", "data warehouse", "data lake"],
    "pandas":           ["dataframes"],
    "numpy":            [],
    "matplotlib":       ["seaborn", "plotly", "data visualization"],
    "spark":            ["apache spark", "pyspark", "hadoop", "hive", "hbase",
                         "big data", "databricks"],
    "airflow":          ["apache airflow", "workflow orchestration", "dbt", "luigi"],
    # ── Testing ────────────────────────────────────────────────────────────
    "testing":          ["unit testing", "tdd", "test driven development",
                         "pytest", "jest", "mocha", "junit", "selenium",
                         "cypress", "playwright", "end-to-end testing", "e2e"],
    # ── System design ──────────────────────────────────────────────────────
    "system design":    ["distributed systems", "scalability", "high availability",
                         "load balancing", "caching strategy", "message queue",
                         "kafka", "rabbitmq", "celery", "event driven"],
    # ── Security ───────────────────────────────────────────────────────────
    "security":         ["cybersecurity", "oauth", "jwt", "authentication",
                         "authorization", "ssl", "tls", "encryption", "owasp"],
    # ── Mobile ─────────────────────────────────────────────────────────────
    "android":          ["android sdk", "android development"],
    "ios":              ["ios development", "xcode", "objective-c"],
    "flutter":          ["dart"],
    "react native":     [],
    # ── Collaboration ──────────────────────────────────────────────────────
    "agile":            ["scrum", "kanban", "sprint", "jira", "confluence"],
}

# Build a flat reverse-lookup: any_term → canonical_skill
_TERM_TO_CANONICAL: dict[str, str] = {}
for _canonical, _synonyms in SKILL_SYNONYMS.items():
    _TERM_TO_CANONICAL[_canonical] = _canonical
    for _syn in _synonyms:
        _TERM_TO_CANONICAL[_syn] = _canonical

SKILL_HIERARCHY: dict[str, list[str]] = {
    "frontend":         ["react", "vue", "angular", "html", "css", "javascript",
                         "typescript", "svelte", "redux"],
    "backend":          ["python", "django", "flask", "fastapi", "java", "spring",
                         "node.js", "rest api", "graphql", "grpc", "microservices"],
    "database":         ["sql", "mongodb", "redis", "elasticsearch", "cassandra",
                         "dynamodb", "firebase", "neo4j"],
    "devops":           ["docker", "kubernetes", "aws", "azure", "gcp", "terraform",
                         "ansible", "jenkins", "linux"],
    "machine learning": ["machine learning", "tensorflow", "pytorch", "scikit-learn",
                         "nlp", "computer vision", "data analysis", "pandas",
                         "numpy", "spark", "airflow"],
    "mobile":           ["android", "ios", "flutter", "react native", "swift", "kotlin"],
    "security":         ["security"],
    "testing":          ["testing"],
}


# ═══════════════════════════════════════════════════════════════════════════
#  REGEX PATTERNS
# ═══════════════════════════════════════════════════════════════════════════

# Experience year patterns
_EXP_DIRECT_RE  = re.compile(r"(\d{1,2})\+?\s*years?\s+(?:of\s+)?(?:experience|exp(?:erience)?)",
                              re.IGNORECASE)
_DATE_RANGE_RE  = re.compile(r"(\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
                              r"(?:\s+\d{4})?\s*[-–—/]\s*"
                              r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
                              r"(?:\s+\d{4})?|"
                              r"(\d{4})\s*[-–—]\s*(\d{4}|present|current|till\s*date|now))",
                              re.IGNORECASE)
_YEAR_RANGE_RE  = re.compile(r"(\d{4})\s*[-–—]\s*(\d{4}|present|current|till\s*date|now)",
                              re.IGNORECASE)

# Role title patterns — matches typical job title lines
_ROLE_TITLE_RE  = re.compile(
    r"(?:^|\n)\s*(.{5,60}?)\s*(?:\||at|@|,|-)\s*(.{3,60}?)\s*"
    r"(?:\d{4}|\(|\[|$)",
    re.MULTILINE,
)
_ROLE_KEYWORD_RE = re.compile(
    r"\b(software|senior|junior|lead|principal|staff|engineer|developer|architect|"
    r"manager|analyst|scientist|consultant|intern|associate|director|head|vp|cto|"
    r"full.?stack|front.?end|back.?end|devops|sre|data|ml|ai|cloud|security)\b",
    re.IGNORECASE,
)

# Contact
EMAIL_RE        = re.compile(r"[\w.+\-]+@[\w\-]+\.[a-zA-Z]{2,}")
PHONE_RE        = re.compile(r"(?:\+?\d[\d\s\-().]{8,}?\d)")
LINKEDIN_RE     = re.compile(r"linkedin\.com/in/[\w\-]+", re.IGNORECASE)
GITHUB_RE       = re.compile(r"github\.com/[\w\-]+", re.IGNORECASE)
URL_RE          = re.compile(r"https?://[^\s]+")

# Education
_DEGREE_PATTERNS = [
    (re.compile(r"\b(ph\.?\s*d|doctorate)\b", re.IGNORECASE),          "PhD"),
    (re.compile(r"\b(m\.?\s*tech|master\s+of\s+tech(?:nology)?)\b",
                re.IGNORECASE),                                          "M.Tech"),
    (re.compile(r"\b(mba|master\s+of\s+business)\b", re.IGNORECASE),   "MBA"),
    (re.compile(r"\b(m\.?\s*s\.?|m\.?\s*sc\.?|master\s+of\s+science)\b",
                re.IGNORECASE),                                          "M.Sc"),
    (re.compile(r"\b(m\.?\s*e\.?|master\s+of\s+engineering)\b",
                re.IGNORECASE),                                          "M.E."),
    (re.compile(r"\b(b\.?\s*tech|bachelor\s+of\s+tech(?:nology)?)\b",
                re.IGNORECASE),                                          "B.Tech"),
    (re.compile(r"\b(b\.?\s*e\.?|bachelor\s+of\s+engineering)\b",
                re.IGNORECASE),                                          "B.E."),
    (re.compile(r"\b(b\.?\s*s\.?|b\.?\s*sc\.?|bachelor\s+of\s+science)\b",
                re.IGNORECASE),                                          "B.Sc"),
    (re.compile(r"\b(b\.?\s*c\.?a\.?|bachelor\s+of\s+computer)\b",
                re.IGNORECASE),                                          "BCA"),
    (re.compile(r"\b(m\.?\s*c\.?a\.?|master\s+of\s+computer)\b",
                re.IGNORECASE),                                          "MCA"),
    (re.compile(r"\bdiploma\b", re.IGNORECASE),                         "Diploma"),
    (re.compile(r"\b(b\.?\s*com|b\.?\s*a\.?|bachelor)\b", re.IGNORECASE), "Bachelor"),
]

# Certification keywords — mapped to standardised labels
_CERT_MAP: dict[str, str] = {
    "aws certified":            "AWS Certified",
    "amazon web services cert": "AWS Certified",
    "google certified":         "Google Certified",
    "google cloud certified":   "Google Cloud Certified",
    "microsoft certified":      "Microsoft Certified",
    "azure certified":          "Microsoft Azure Certified",
    "cisco certified":          "Cisco Certified",
    "ccna":                     "CCNA",
    "ccnp":                     "CCNP",
    "pmp":                      "PMP",
    "prince2":                  "PRINCE2",
    "certified scrum master":   "Certified ScrumMaster",
    "csm":                      "Certified ScrumMaster",
    "certified scrum":          "Certified Scrum",
    "oracle certified":         "Oracle Certified",
    "comptia":                  "CompTIA",
    "security+":                "CompTIA Security+",
    "ceh":                      "CEH",
    "cissp":                    "CISSP",
    "tensorflow developer":     "TensorFlow Developer Certificate",
    "deep learning specialization": "Deep Learning Specialization",
    "machine learning specialization": "ML Specialization",
    "data science":             "Data Science Certificate",
}

# Name heuristics — title-case word sequences near the top of the document
_NAME_RE = re.compile(
    r"^[ \t]*([A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20}){1,3})[ \t]*$",
    re.MULTILINE,
)


# ═══════════════════════════════════════════════════════════════════════════
#  CORE HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def normalize_skill(skill: str) -> str:
    """Return the canonical form of a skill string."""
    cleaned = skill.lower().strip().rstrip(".,;:")
    return _TERM_TO_CANONICAL.get(cleaned, cleaned)


# Alias used by ranker.py for JD skill extraction (same as regex extraction)
def extract_skills_nlp(text: str) -> list[str]:
    """Alias for extract_skills_regex — used for NLP-based JD parsing."""
    return extract_skills_regex(text)


def enrich_skill_categories(skills: list[str]) -> dict[str, list[str]]:
    """Assign each skill to its domain category."""
    categories: dict[str, list[str]] = {}
    normalized = {normalize_skill(s) for s in skills}
    for domain, domain_skills in SKILL_HIERARCHY.items():
        matched = sorted(normalized & set(domain_skills))
        if matched:
            categories[domain] = matched
    return categories


# ═══════════════════════════════════════════════════════════════════════════
#  LAYER 1 — REGEX / KEYWORD EXTRACTION  (zero extra dependencies)
# ═══════════════════════════════════════════════════════════════════════════

def extract_skills_regex(text: str) -> list[str]:
    """
    Scan text for all known skills using whole-word regex matching.
    Handles multi-word terms (e.g. "machine learning", "rest api") correctly.
    """
    found: set[str] = set()
    text_lower = text.lower()

    # Sort by length DESC so longer phrases are matched before substrings
    all_terms = sorted(_TERM_TO_CANONICAL.keys(), key=len, reverse=True)
    for term in all_terms:
        # Boundary check: use \b only when term starts/ends with \w char
        left_b  = r"\b" if term[0].isalnum()  or term[0] == "_" else ""
        right_b = r"\b" if term[-1].isalnum() or term[-1] == "_" else ""
        pattern = left_b + re.escape(term) + right_b
        if re.search(pattern, text_lower):
            found.add(_TERM_TO_CANONICAL[term])

    return sorted(found)


def extract_experience_regex(text: str) -> dict[str, Any]:
    """
    Extract total years of experience and work-period timeline via regex.
    Also attempts to extract role titles.
    """
    total_years  = 0
    timeline: list[dict] = []
    roles: list[dict]    = []

    # 1. Direct "X years of experience" statements
    for m in _EXP_DIRECT_RE.finditer(text):
        yrs = int(m.group(1))
        total_years = max(total_years, yrs)

    # 2. Date ranges  e.g. "2019 - 2022"  or  "2020 - Present"
    for m in _YEAR_RANGE_RE.finditer(text):
        try:
            start = int(m.group(1))
            end_raw = m.group(2).lower().strip()
            end = 2025 if end_raw in ("present", "current", "now") or "date" in end_raw \
                       else int(end_raw)
            if 1980 <= start <= 2025 and start <= end <= 2025:
                duration = end - start
                timeline.append({"start": start, "end": end,
                                  "duration_years": duration})
                total_years = max(total_years, duration)
        except ValueError:
            pass

    # 3. Estimate total from timeline if direct statement is missing
    if timeline and total_years == 0:
        years_set = sorted({t["start"] for t in timeline} |
                           {t["end"] for t in timeline if t["end"] != 2025})
        if len(years_set) >= 2:
            total_years = years_set[-1] - years_set[0]

    # 4. Role title extraction (heuristic)
    for line in text.split("\n"):
        line = line.strip()
        if 5 < len(line) < 80 and _ROLE_KEYWORD_RE.search(line):
            # Avoid picking up skill lists or education lines
            if not any(deg in line.lower() for deg in ("bachelor", "master", "phd", "b.tech")):
                roles.append({"title": line, "company": "", "description": ""})
    roles = _dedupe_roles(roles)[:8]

    return {
        "total_years": total_years,
        "timeline":    timeline,
        "roles":       roles,
    }


def _dedupe_roles(roles: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out  = []
    for r in roles:
        key = r["title"].lower()[:40]
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def extract_education_regex(text: str) -> list[dict]:
    """
    Extract highest-confidence degree entries with institution & year context.
    """
    entries: list[dict] = []
    seen_degrees: set[str] = set()

    for pattern, label in _DEGREE_PATTERNS:
        for m in pattern.finditer(text):
            if label in seen_degrees:
                break
            seen_degrees.add(label)
            # Grab the surrounding line for institution / year
            start_pos = max(0, m.start() - 60)
            end_pos   = min(len(text), m.end() + 120)
            ctx       = text[start_pos:end_pos].strip()
            ctx_line  = ctx.split("\n")[0]

            # Try to pull a 4-digit year from context
            year_m = re.search(r"\b(19\d{2}|20\d{2})\b", ctx)
            year   = year_m.group(1) if year_m else ""

            # Heuristic: institution is usually the longest capitalised token nearby
            institution = _extract_institution(ctx_line, m.group())

            entries.append({
                "degree":      label,
                "institution": institution,
                "year":        year,
                "context":     ctx_line[:120],
            })
    return entries


def _extract_institution(line: str, degree_match: str) -> str:
    """Best-effort institution name from a single line."""
    line_clean = re.sub(re.escape(degree_match), "", line, flags=re.IGNORECASE).strip()
    # Remove years and common punctuation
    line_clean = re.sub(r"\b(19|20)\d{2}\b", "", line_clean)
    line_clean = re.sub(r"[|,\-–—()\[\]]", " ", line_clean).strip()
    # Return the longest capitalised phrase
    phrases = [p.strip() for p in re.split(r"\s{2,}", line_clean) if len(p.strip()) > 4]
    if phrases:
        return max(phrases, key=len)[:80]
    return ""


def extract_certifications_regex(text: str) -> list[str]:
    """Map certification mentions to canonical labels."""
    found: set[str] = set()
    text_lower = text.lower()
    for keyword, label in _CERT_MAP.items():
        if keyword in text_lower:
            found.add(label)
    return sorted(found)


def extract_projects_regex(text: str, sections: dict) -> list[dict]:
    """
    Extract project entries from the Projects section (preferred) or full text.
    Detects project name, description snippet, and tech-stack tokens.
    """
    source = sections.get("projects", "") or text
    projects: list[dict] = []

    # Pattern 1: explicit "Project:" or "• Project name" bullets
    bullet_re = re.compile(
        r"(?:^|\n)\s*(?:[•\-*▪➢→]\s*|(?:project\s*\d*\s*[:\-]\s*))(.{5,120})",
        re.IGNORECASE | re.MULTILINE,
    )
    for m in bullet_re.finditer(source):
        name = m.group(1).strip().split("\n")[0][:100]
        if len(name) > 4:
            projects.append(_make_project(name, source))

    # Pattern 2: bold-like ALL-CAPS short lines as project titles
    if not projects:
        for line in source.split("\n"):
            line = line.strip()
            if 4 < len(line) < 70 and line == line.upper() and line[0].isalpha():
                projects.append(_make_project(line.title(), source))

    # Deduplicate and cap
    seen: set[str] = set()
    unique = []
    for p in projects:
        key = p["name"].lower()[:30]
        if key not in seen:
            seen.add(key)
            unique.append(p)

    return unique[:10]


def _make_project(name: str, context_text: str) -> dict:
    """Build a project dict with tech-stack extracted from context."""
    skills_in_context = extract_skills_regex(context_text[:500])
    return {"name": name, "description": "", "tech_stack": skills_in_context[:8]}


def extract_contact_regex(text: str) -> dict[str, str]:
    """Extract email, phone, LinkedIn, GitHub and candidate name."""
    email_m    = EMAIL_RE.search(text)
    phone_m    = PHONE_RE.search(text)
    linkedin_m = LINKEDIN_RE.search(text)
    github_m   = GITHUB_RE.search(text)

    # Name: look in the first 20 lines for a plausible "Firstname Lastname" line
    name = ""
    for line in text.split("\n")[:20]:
        nm = _NAME_RE.match(line)
        if nm:
            candidate = nm.group(1).strip()
            # Reject lines that look like section headers or job titles
            if (len(candidate.split()) in (2, 3)
                    and not any(kw in candidate.lower()
                                for kw in ("resume", "curriculum", "vitae", "profile",
                                           "experience", "education", "summary",
                                           "skills", "technical", "objective",
                                           "contact", "certifications", "projects",
                                           "references", "languages", "interests",
                                           "achievements", "awards"))):
                name = candidate
                break

    return {
        "name":     _validate_name(name),
        "email":    email_m.group()    if email_m    else "",
        "phone":    phone_m.group().strip()  if phone_m    else "",
        "linkedin": linkedin_m.group() if linkedin_m else "",
        "github":   github_m.group()   if github_m   else "",
    }


def build_profile_regex(text: str, sections: dict) -> dict:
    """
    Full Layer-1 profile from pure regex + keyword matching.
    No external library dependencies.
    """
    skills_text = sections.get("skills", "") + "\n" + text
    exp_text    = sections.get("experience", "") + "\n" + text

    skills         = extract_skills_regex(skills_text)
    experience     = extract_experience_regex(exp_text)
    education      = extract_education_regex(sections.get("education", text))
    certifications = extract_certifications_regex(sections.get("certifications", text))
    projects       = extract_projects_regex(text, sections)
    contact        = extract_contact_regex(text)

    return {
        "skills":            skills,
        "skill_categories":  enrich_skill_categories(skills),
        "experience_years":  experience,
        "projects":          projects,
        "education":         education,
        "certifications":    certifications,
        "contact":           contact,
        "summary":           "",
        "extraction_method": "regex_layer1",
    }


# ═══════════════════════════════════════════════════════════════════════════
#  LAYER 2 — NLTK ENRICHMENT  (adds tokenization, POS, n-grams)
# ═══════════════════════════════════════════════════════════════════════════

def _extract_skills_ngrams(text: str) -> list[str]:
    """
    Use NLTK bigrams / trigrams to catch multi-word skills missed by plain regex.
    Returns skills in canonical form.
    """
    if not _NLTK_READY:
        return []
    try:
        import nltk
        from nltk.util import ngrams as nltk_ngrams

        tokens = nltk.word_tokenize(text.lower())
        found: set[str] = set()

        for n in (1, 2, 3):
            for gram in nltk_ngrams(tokens, n):
                phrase = " ".join(gram)
                if phrase in _TERM_TO_CANONICAL:
                    found.add(_TERM_TO_CANONICAL[phrase])

        return sorted(found)
    except Exception as e:
        logger.debug(f"NLTK n-gram extraction failed (non-fatal): {e}")
        return []


_NAME_STOP_WORDS = {
    # Section headers
    "technical", "skills", "experience", "education", "summary", "objective",
    "contact", "references", "certifications", "projects", "languages",
    "interests", "achievements", "awards", "publications",
    # Job titles / seniority
    "engineer", "developer", "manager", "analyst", "designer", "architect",
    "consultant", "specialist", "lead", "senior", "junior", "intern",
    "director", "president", "vp", "cto", "ceo", "coo", "officer",
    "scientist", "researcher", "associate", "assistant", "coordinator",
    "administrator", "executive", "head", "principal", "staff",
    # Tech / domain words that appear near names in headers
    "full", "stack", "backend", "frontend", "software", "data", "ai",
    "ml", "devops", "cloud", "mobile", "web",
    # Generic filler
    "resume", "cv", "curriculum", "vitae", "profile", "updated", "final",
    "unknown",
}


def _validate_name(name: str) -> str:
    """
    Validate and normalise an extracted candidate name string.

    Accepts: "John Smith", "Amal A P", "PRIYA KUMAR" (returns normalised form)
    Rejects: job titles, numbers, all-single-initials, empty, too long

    Returns normalised name string if valid, empty string otherwise.
    """
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
    if any(w.lower() in _NAME_STOP_WORDS for w in words):
        return ""
    if not words[0][0].isalpha():
        return ""
    # Require at least one word longer than 1 char (rejects bare "A B" initials)
    if all(len(w) <= 1 for w in words):
        return ""

    def _fix_word(w: str) -> str:
        if len(w) == 1:
            return w.upper()           # single initial stays uppercase
        return w.capitalize() if w.isupper() else w  # "AMAL" → "Amal", "Amal" unchanged

    return " ".join(_fix_word(w) for w in words)


def extract_name_focused(text: str) -> str:
    """
    Dedicated focused LLM call that extracts ONLY the candidate's name.
    Used as a final fallback after regex + NLTK + full Groq extraction all miss or
    return an invalid name. Sends only the first 50 lines to minimise tokens.
    Returns a validated name string, or empty string on failure.
    """
    from django.conf import settings as _settings
    api_key = _settings.GROQ_API_KEY
    if not api_key:
        return ""

    first_section = "\n".join(text.split("\n")[:50])
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=_settings.GROQ_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Look at the very top of this resume and extract the candidate's full name.\n"
                        "Return ONLY the name — for example: 'John Smith' or 'Amal A P'.\n"
                        "Do NOT include job titles, degrees, company names, or any other words.\n"
                        "If no clear name is visible, return exactly: UNKNOWN\n\n"
                        f"Resume (top section):\n{first_section}"
                    ),
                }
            ],
            temperature=0.0,
            max_tokens=15,
        )
        raw = response.choices[0].message.content.strip()
        validated = _validate_name(raw)
        if validated:
            logger.info("Focused name extraction succeeded: %s", validated)
        return validated
    except Exception as e:
        logger.debug("Focused name extraction failed (non-fatal): %s", e)
        return ""


def _extract_name_nltk(text: str) -> str:
    """
    POS-tag the first 30 tokens to find NNP sequences — a likely person name.
    Stops collecting at the first job-title or section-header word.
    """
    if not _NLTK_READY:
        return ""
    try:
        import nltk
        first_block = " ".join(text.split()[:40])
        tokens = nltk.word_tokenize(first_block)
        tagged = nltk.pos_tag(tokens)

        name_parts: list[str] = []
        for word, pos in tagged[:30]:
            if word.lower() in _NAME_STOP_WORDS:
                break  # hit a role/header word — stop here
            if pos in ("NNP", "NNPS") and word.isalpha():
                name_parts.append(word)
            elif name_parts:
                break

        candidate = " ".join(name_parts)
        if 2 < len(candidate) < 50 and 1 < len(name_parts) <= 4:
            return candidate
    except Exception as e:
        logger.debug(f"NLTK name extraction failed (non-fatal): {e}")
    return ""


def _extract_keywords_tfidf(text: str, top_n: int = 20) -> list[str]:
    """
    Use sklearn TF-IDF on the resume text to surface high-signal words
    not in the fixed ontology.  Returns raw keyword strings.
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        import numpy as np

        # Treat the resume as a single document; use character n-grams to handle
        # hyphenated terms like "full-stack", "end-to-end"
        vect = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 3),
            min_df=1,
            max_features=200,
            stop_words="english",
        )
        X = vect.fit_transform([text])
        scores = np.asarray(X.todense()).flatten()
        feature_names = vect.get_feature_names_out()
        top_indices   = scores.argsort()[::-1][:top_n]
        keywords = [feature_names[i] for i in top_indices if scores[i] > 0]

        # Only return keywords that map to a known canonical skill
        skills = []
        for kw in keywords:
            canonical = _TERM_TO_CANONICAL.get(kw.lower())
            if canonical:
                skills.append(canonical)
        return skills
    except Exception as e:
        logger.debug(f"TF-IDF keyword extraction failed (non-fatal): {e}")
        return []


def enrich_with_nltk(base_profile: dict, text: str) -> dict:
    """
    Layer-2 enrichment: adds n-gram skills, TF-IDF keywords, NNP name.
    Mutates and returns the profile dict.
    """
    # Additional skills from n-grams
    ngram_skills  = _extract_skills_ngrams(text)
    tfidf_skills  = _extract_keywords_tfidf(text)
    extra_skills  = set(ngram_skills) | set(tfidf_skills)

    if extra_skills:
        merged_skills = sorted(set(base_profile.get("skills", [])) | extra_skills)
        base_profile["skills"]           = merged_skills
        base_profile["skill_categories"] = enrich_skill_categories(merged_skills)

    # Better name detection via POS tagging (only fills if regex found nothing valid)
    if not base_profile.get("contact", {}).get("name"):
        nltk_name = _validate_name(_extract_name_nltk(text))
        if nltk_name:
            base_profile.setdefault("contact", {})["name"] = nltk_name

    base_profile["extraction_method"] = base_profile.get("extraction_method", "") + "+nltk"
    return base_profile


# ═══════════════════════════════════════════════════════════════════════════
#  LAYER 3 — GROQ LLM  (structures, summarises, fills remaining gaps)
# ═══════════════════════════════════════════════════════════════════════════

def extract_with_groq(text: str) -> dict | None:
    """
    Use Groq LLM for high-quality structured extraction.
    Returns a profile dict or None when the API is unavailable.
    """
    from django.conf import settings as _settings
    api_key = _settings.GROQ_API_KEY
    if not api_key:
        logger.info("GROQ_API_KEY not set — using regex+NLTK only.")
        return None

    try:
        from groq import Groq
        client = Groq(api_key=api_key)

        prompt = (
            "You are a precise resume parser. Extract structured information from the "
            "resume text below and return ONLY a valid JSON object with these exact keys:\n"
            "- skills: list of strings (normalise synonyms, lowercase)\n"
            "- experience_years: {total_years: int, roles: [{title, company, years, description}]}\n"
            "- projects: [{name, description, tech_stack: [string]}]\n"
            "- education: [{degree, institution, year}]\n"
            "- certifications: list of strings\n"
            "- contact: {name, email, phone, linkedin, github}\n"
            "- summary: string (2–3 sentence professional summary)\n\n"
            f"Resume:\n{text[:3000]}"
        )

        response = client.chat.completions.create(
            model=_settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": "Return only valid JSON. No explanation."},
                {"role": "user",   "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=1000,
        )

        profile = json.loads(response.choices[0].message.content)
        profile["extraction_method"] = "groq_llm"

        if isinstance(profile.get("skills"), list):
            profile["skills"] = [normalize_skill(s) for s in profile["skills"]]
            profile["skill_categories"] = enrich_skill_categories(profile["skills"])

        # Validate the LLM-extracted name before propagating
        contact = profile.get("contact", {})
        if isinstance(contact, dict):
            contact["name"] = _validate_name(contact.get("name", ""))
            profile["contact"] = contact

        return profile

    except Exception as e:
        logger.error(f"Groq extraction failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════
#  MERGE HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _merge_profiles(base: dict, overlay: dict) -> dict:
    """
    Merge overlay into base.  Lists are unioned; scalars from overlay win
    only when base is empty/zero.
    """
    merged = base.copy()

    # Skills — always union
    base_skills    = set(merged.get("skills", []))
    overlay_skills = set(overlay.get("skills", []))
    merged["skills"] = sorted(base_skills | overlay_skills)
    merged["skill_categories"] = enrich_skill_categories(merged["skills"])

    # Experience — prefer whichever has more roles / years
    base_exp    = merged.get("experience_years", {})
    overlay_exp = overlay.get("experience_years", {})
    if isinstance(overlay_exp, dict):
        base_years    = base_exp.get("total_years", 0)   if isinstance(base_exp, dict) else 0
        overlay_years = overlay_exp.get("total_years", 0)
        if overlay_years > base_years:
            merged["experience_years"] = overlay_exp
        # Merge roles lists
        base_roles    = base_exp.get("roles", [])    if isinstance(base_exp, dict) else []
        overlay_roles = overlay_exp.get("roles", [])
        combined_roles = {r.get("title", "").lower(): r
                          for r in (base_roles + overlay_roles)}.values()
        merged["experience_years"]["roles"] = list(combined_roles)[:10]

    # Projects — union by name
    base_projs    = {p.get("name", "").lower(): p for p in merged.get("projects", [])}
    overlay_projs = {p.get("name", "").lower(): p for p in overlay.get("projects", [])}
    base_projs.update(overlay_projs)
    merged["projects"] = list(base_projs.values())[:10]

    # Education — prefer overlay if richer
    if len(overlay.get("education", [])) > len(merged.get("education", [])):
        merged["education"] = overlay["education"]

    # Certifications — union
    merged["certifications"] = sorted(
        set(merged.get("certifications", [])) | set(overlay.get("certifications", []))
    )

    # Contact — fill blanks; for name, prefer validated LLM result over regex
    base_contact    = merged.get("contact", {})
    overlay_contact = overlay.get("contact", {})
    if isinstance(base_contact, dict) and isinstance(overlay_contact, dict):
        # Name: pick the best valid option — LLM (overlay) > regex/NLTK (base) > empty
        validated_overlay = _validate_name(overlay_contact.get("name", ""))
        validated_base    = _validate_name(base_contact.get("name", ""))
        if validated_overlay:
            base_contact["name"] = validated_overlay   # LLM name is valid — use it
        elif validated_base:
            base_contact["name"] = validated_base      # keep regex/NLTK name
        else:
            base_contact["name"] = ""                  # clear invalid; filename fallback applies
        # Other contact fields: fill blanks as before
        for key in ("email", "phone", "linkedin", "github"):
            if not base_contact.get(key):
                base_contact[key] = overlay_contact.get(key, "")
        merged["contact"] = base_contact

    # Summary — prefer overlay if non-empty
    if not merged.get("summary") and overlay.get("summary"):
        merged["summary"] = overlay["summary"]

    return merged


# ═══════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════

def extract_profile(text: str, sections: dict | None = None) -> dict:
    """
    Main entry point.

    Runs all three extraction layers and merges results:
      Layer 1 (regex)  → always runs, provides the base profile
      Layer 2 (NLTK)   → enriches with n-grams, POS names, TF-IDF
      Layer 3 (Groq)   → provides LLM structure + summary (if API key present)

    Returns a single merged profile dict.
    """
    if not text or len(text.strip()) < 20:
        return _empty_profile()

    sections = sections or {}

    # ── Layer 1: regex baseline ────────────────────────────────────────────
    profile = build_profile_regex(text, sections)

    # ── Layer 2: NLTK enrichment ───────────────────────────────────────────
    profile = enrich_with_nltk(profile, text)

    # ── Layer 3: Groq LLM ─────────────────────────────────────────────────
    llm_profile = extract_with_groq(text)
    if llm_profile:
        profile = _merge_profiles(profile, llm_profile)
        profile["extraction_method"] = "regex+nltk+groq_merged"

    # Name fallback is handled by CandidateProfile.candidate_name property
    # (uses resume filename). No extra Groq round-trip needed here.

    return profile


def _empty_profile() -> dict:
    return {
        "skills":            [],
        "skill_categories":  {},
        "experience_years":  {"total_years": 0, "timeline": [], "roles": []},
        "projects":          [],
        "education":         [],
        "certifications":    [],
        "contact":           {"name": "", "email": "", "phone": "",
                              "linkedin": "", "github": ""},
        "summary":           "",
        "extraction_method": "empty",
    }
