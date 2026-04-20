# Technical Report — Smart Talent Selection Engine

**Version:** 1.0  
**Date:** 2026-04-20  
**Status:** Development Complete — Pre-GitHub Release

---

## Table of Contents

1. [System Overview](#system-overview)
2. [System Design & Data Flow](#system-design--data-flow)
3. [Module Breakdown](#module-breakdown)
4. [AI Pipeline](#ai-pipeline)
5. [Database Schema](#database-schema)
6. [API Contract](#api-contract)
7. [Performance Analysis](#performance-analysis)
8. [Celery Status](#celery-status)
9. [NLP Stack Status](#nlp-stack-status)
10. [NLP Stack Status](#nlp-stack-status)
11. [Seed Data Command](#seed-data-command)
12. [Security Model](#security-model)
11. [Frontend Architecture](#frontend-architecture)
12. [Configuration Reference](#configuration-reference)

---

## System Overview

The Smart Talent Selection Engine is a full-stack AI hiring platform built with Django 4.2 (backend), React 18 + Vite 6 (frontend), and Groq's LLM API as the intelligence layer. It replaces keyword-based applicant tracking with semantic understanding and explainable scoring.

The system is Python 3.13 compatible. It deliberately avoids spaCy (which lacks Python 3.13 wheels) and instead implements NLP using NLTK, scikit-learn, and sentence-transformers — all of which ship pre-built wheels for Python 3.13.

---

## System Design & Data Flow

### End-to-End Request Flow

```
[1] File Upload
    Browser → POST /api/resumes/upload/
    → resumes/views.py: validate extension, size, SHA-256 dedup
    → Resume model saved (status=pending)
    → parse_resume_task dispatched (Celery)

[2] Async Parsing (parse_resume_task)
    → ai_pipeline/parser.py: file → raw text
    → ai_pipeline/extractor.py: 3-layer NLP → structured_profile JSON
    → ai_pipeline/embeddings.py: profile_text → 384-dim vector → FAISS
    → CandidateProfile created (or updated if reparse)
    → Resume status updated to done / error

[3] Job Creation
    POST /api/jobs/ with JD text
    → jobs/views.py: save Job model
    → Groq LLM: parse JD → parsed_requirements JSON
    (required_skills, preferred_skills, min_experience_years, education_required, role_context)

[4] Ranking
    POST /api/jobs/{id}/run-ranking/
    → RankingRun created (status=running)
    → rank_candidates_task dispatched
    → ai_pipeline/ranker.py: compute_total_score() per candidate
    → Groq LLM: generate 2-sentence justification per candidate
    → RankingResult upserted (unique: job + candidate)
    → RankingRun updated (status=done)

[5] Results Display
    GET /api/ranking/results/?job_id={id}&min_score={n}&skills={csv}
    → RankingResult queryset, annotated, filtered, serialized
    → Frontend: CandidateCard grid with score bars and justifications
```

### Deduplication Strategy

Every uploaded file is hashed with SHA-256 before writing to disk. If the hash already exists in the database, the file is rejected as a duplicate and the existing resume ID is returned. This prevents the same resume from being parsed and embedded twice, regardless of filename.

---

## Module Breakdown

### resumes — Upload & Parsing

**Models:** `Resume`  
**Key fields:** `file`, `filename`, `file_type`, `job_role`, `status` (pending/processing/done/error), `parse_confidence` (0–1), `raw_text`, `parsed_sections` (JSON), `content_hash` (SHA-256, indexed)

**Responsibilities:**
- Receive bulk file uploads via multipart form
- Validate MIME extensions: `.pdf`, `.docx`, `.jpg`, `.jpeg`, `.png`
- Enforce 10 MB per-file size cap
- Detect and reject duplicate files by content hash
- Dispatch `parse_resume_task` per accepted file
- Expose `/stats/` aggregation endpoint for the dashboard
- `/reparse/` action to retry failed files

**File routing logic (resumes/views.py):**
Files are stored under `media/resumes/<job_role>/<safe_filename>`. Filenames are sanitized by stripping path components (`os.path.basename`) and removing null bytes. Directory traversal patterns are blocked explicitly.

---

### jobs — Job Description Management

**Models:** `Job`  
**Key fields:** `title`, `description`, `required_skills` (JSON array), `preferred_skills` (JSON array), `min_experience_years`, `education_required`, `employment_type` (full_time/part_time/contract/internship), `is_active`, `parsed_requirements` (JSON — Groq output)

**Responsibilities:**
- CRUD operations on job descriptions
- On job creation or update: call Groq to extract structured requirements into `parsed_requirements`
- `/run-ranking/` action: dispatch `rank_candidates_task`
- `/suggest-jd/` action: call Groq to generate improvement suggestions for the JD text

**parsed_requirements schema (Groq output):**
```
{
  required_skills: [str],
  preferred_skills: [str],
  min_experience_years: int,
  education_required: str,
  key_responsibilities: [str],
  role_context: str
}
```

---

### candidates — Profile Management

**Models:** `CandidateProfile`, `RecruiterFeedback`

**CandidateProfile fields:** `resume` (OneToOne FK), `structured_profile` (JSON — full extraction output), `embedding_vector` (JSON list of floats), `profile_text` (text used for embedding), `is_shortlisted`, `recruiter_notes`, `bias_flags` (JSON list)

**RecruiterFeedback fields:** `candidate` (FK), `job` (FK), `action` (shortlisted/rejected/interview/hired), `notes` — unique per (candidate, job) pair

**Responsibilities:**
- List and filter candidate profiles
- `/vs-jd/` endpoint: compare candidate skills + score against a specific job's requirements
- `/feedback/` endpoint: record recruiter decision; sets `is_shortlisted` flag on shortlisted/interview/hired
- `/search/` endpoint: convert query text to embedding → FAISS search → return top-k candidates by semantic similarity

**candidate_name resolution:** The `candidate_name` property on `CandidateProfile` looks for contact name in the structured profile. If no name was extracted, it falls back to the resume filename (without extension). This means candidates from generic filenames (e.g., `resume.pdf`) display as `Candidate #N`.

---

### ranking — Scoring Engine

**Models:** `RankingResult`, `RankingRun`

**RankingResult fields:** `job` (FK), `candidate` (FK), `total_score`, `skill_score`, `experience_score`, `project_score`, `education_score`, `score_breakdown` (JSON detail), `justification` (text), `rank_position` — unique per (job, candidate)

**RankingRun fields:** `job` (FK), `status` (running/done/error), `total_candidates`, `processed_candidates`, `error_message`, `started_at`, `finished_at`

**Responsibilities:**
- `rank_candidates_task`: score all `done`-status candidates for a job, bulk upsert `RankingResult`, assign `rank_position` by descending score
- `quick-rank` endpoint: synchronous ranking of up to 200 candidates using provided JD text (no stored job required)
- Filter API: `job_id`, `min_score`, `skill` (single) or `skills` (AND-logic comma-separated list)

---

### ai_pipeline — Intelligence Layer

Four modules forming a sequential pipeline. Described in detail in the [AI Pipeline](#ai-pipeline) section below.

---

## AI Pipeline

### Stage 1 — Document Parsing (parser.py)

Converts raw files to plain text using library-specific backends:

| Format | Primary | Fallback |
|---|---|---|
| PDF | pdfplumber (layout-aware) | pypdf (raw text) |
| DOCX | python-docx (preserves tables) | — |
| Images (JPG, PNG) | pytesseract OCR | — |

The parser also segments the raw text into sections (Experience, Education, Skills, Projects, Contact) using header-pattern matching.

---

### Stage 2 — Profile Extraction (extractor.py)

Three independent layers run sequentially; results are merged into a single profile dict.

**Layer 1 — Regex (always runs)**
- Skills: matched against a 165+ canonical skill set with synonym normalization (`normalize_skill()`)
- Multi-word skill patterns with word-boundary guards
- Experience years: regex on year statements and date ranges
- Education: pattern matching for degree types (PhD, Master, Bachelor, Diploma)
- Contact: email and phone extraction

**Layer 2 — NLTK Enrichment**
- N-gram extraction (bigrams + trigrams) for multi-word skills missed by single-token regex
- POS tagging (`nltk.pos_tag`) to identify proper noun sequences (NNP tags) for name extraction
- TF-IDF keyword ranking (`sklearn.TfidfVectorizer`) to identify the most distinctive terms per resume section
- NLTK data bootstrapped on first run: `punkt_tab`, `averaged_perceptron_tagger_eng`, `stopwords`, `wordnet`

**Layer 3 — Groq LLM (requires GROQ_API_KEY)**
- Model: `llama-3.1-8b-instant`
- Temperature: 0.1 (near-deterministic)
- Max tokens: 1000
- Output: structured JSON with skills, experience_years, projects, education, certifications, contact, summary
- A separate focused call (temperature: 0.0, max tokens: 15) handles name-only extraction when POS tagging fails to find a name

**Merge strategy:** Layer 3 output takes precedence. Layer 1 and Layer 2 skills are unioned with Layer 3 skills. Missing fields from Layer 3 fall back to Layer 1/2 results.

**Skill ontology:**
- 165+ canonical skill terms with synonym maps (e.g., `postgresql → sql`, `tensorflow → machine learning`)
- 8-domain hierarchy: frontend, backend, database, devops, machine learning, mobile, security, testing
- Domain-level credit in scoring allows partial matches when a candidate knows related tools

---

### Stage 3 — Embedding (embeddings.py)

Generates a dense vector representation of each candidate profile for semantic search.

**Backend selection (auto-detected at first use):**

| Priority | Backend | Dimension | Storage |
|---|---|---|---|
| 1 | sentence-transformers + FAISS | 384 | `backend/faiss_index/candidates.index` + `id_mapping.json` |
| 2 | sentence-transformers (no FAISS) | 384 | JSON file (numpy arrays) |
| 3 | sklearn TF-IDF (fallback) | 512 | JSON file |

FAISS uses `IndexFlatIP` (inner product on L2-normalized vectors = cosine similarity). The `id_mapping.json` maps FAISS integer positions to Django candidate IDs, enabling reverse lookup after a search.

The profile text passed to the embedder is a concatenation of skills, summary, role titles, and key keywords — not the raw resume text — to focus similarity on professional attributes.

---

### Stage 4 — Ranking (ranker.py)

**Scoring formula:**

```
Total Score (0–100) =
    Skill Match       × 0.40
  + Experience Depth  × 0.30
  + Project Relevance × 0.20
  + Education & Certs × 0.10
```

**Component algorithms:**

| Component | Key Logic |
|---|---|
| Skill Match | Coverage of required skills (80 pts max) + preferred skill bonus (5 pts each) + domain-level partial credit (10 pts per domain) |
| Experience Depth | Ratio of candidate years to job minimum; role title keyword bonus (+5 per match, max +10) |
| Project Relevance | Tech stack overlap + semantic keyword overlap with JD + quantity bonus per relevant project |
| Education | Degree level (PhD=100, Master=85, Bachelor=70, Diploma=50) × 0.7 + certification bonus (10 pts each, max 30) × 0.3 |

**JD parsing for ranking:**
Before scoring, the job description text is parsed by Groq (temperature: 0.1) to extract `required_skills`, `preferred_skills`, `min_experience_years`, `education_required`, `key_responsibilities`, and `role_context`. This structured output drives all four scoring components.

**Justification generation:**
After scoring, a second Groq call (temperature: 0.3, max tokens: 150) generates a two-sentence natural language justification for each candidate's rank, citing their strongest components and any gaps. This is stored in `RankingResult.justification` and displayed in the UI.

---

## Database Schema

### Entity Relationships

```
Resume ──────────── CandidateProfile
  (1:1, CASCADE)         │
                         ├── RecruiterFeedback ── Job
                         │        (M:1)           (M:1)
                         │
                    RankingResult ──────────────── Job
                         (M:1, CASCADE both)

                    RankingRun ─────────────────── Job
                         (M:1, CASCADE)
```

### Model Summary

| Model | Table | Key Constraints |
|---|---|---|
| Resume | resumes_resume | `content_hash` db_index; status choices enforced |
| CandidateProfile | candidates_candidateprofile | unique OneToOne on `resume` |
| Job | jobs_job | `employment_type` choices enforced |
| RankingResult | ranking_rankingresult | unique_together (job, candidate) |
| RankingRun | ranking_rankingrun | status choices enforced |
| RecruiterFeedback | candidates_recruiterfeedback | unique_together (candidate, job) |

---

## API Contract

### Throttling

| Client | Limit |
|---|---|
| Anonymous | 120 requests/minute |
| Authenticated | 600 requests/minute |

### Pagination

Default page size: 20 items. Use `?page=N` for pagination.

### Error Responses

All errors return standard DRF error objects:
```json
{ "detail": "Error description" }
```
or field-level validation errors:
```json
{ "field_name": ["Error message."] }
```

### Key Endpoint Behaviors

**POST /api/resumes/upload/**
- Accepts: `multipart/form-data` with `files[]` (multiple) + `job_role` (string)
- Returns: `{ queued: [...], duplicates: [...], errors: [...] }`
- Duplicates include the existing resume ID for reference

**GET /api/ranking/results/**
- Filter params: `job_id` (int), `min_score` (float 0–100), `skill` (single string), `skills` (comma-separated AND-logic)
- Results ordered by `rank_position` ascending

**POST /api/ranking/runs/quick-rank/**
- Body: `{ jd_text: string, job_id?: int, limit?: int (max 200, default 50) }`
- Runs synchronously — suitable for small candidate pools without triggering a RankingRun record

---

## Performance Analysis

### Identified Bottlenecks

| Operation | Typical Duration | Notes |
|---|---|---|
| PDF parsing (pdfplumber) | 0.5 – 2s | Scales with page count |
| Image OCR (pytesseract) | 2 – 8s | Highly variable by image quality |
| Groq LLM extraction | 1 – 3s | Network-dependent; parallel with NLTK layer |
| FAISS index update | < 50ms | Negligible up to ~100k vectors |
| Ranking (50 candidates) | 5 – 15s | Groq justification calls dominate |
| Semantic search (k=20) | < 10ms | FAISS inner product is extremely fast |

### Optimizations Applied

- **Groq parallelism:** The LLM call (Layer 3) runs concurrently with NLTK enrichment (Layer 2) using Python threading, hiding most of the Groq latency behind the NLTK processing time.
- **Graceful NLTK bootstrap:** Required NLTK corpora are downloaded on first use, not at import time. Import errors are caught and the layer is skipped if NLTK data is unavailable.
- **FAISS lazy initialization:** The embedding backend (FAISS / numpy / TF-IDF) is selected once at first use and cached. Subsequent operations reuse the loaded index.
- **Bulk upsert in ranking:** `RankingResult` records are upserted in a single bulk operation at the end of `rank_candidates_task`, rather than individual saves per candidate.
- **Frontend polling with backoff:** The Upload page polls processing status every 3 seconds and stops automatically once all tracked IDs reach terminal states (done/error).
- **Vendor chunk splitting:** The Vite production build separates `react`/`react-dom`, `recharts`, and `axios` into dedicated chunks for optimal HTTP caching.

---

## Celery Status

**Current state: Synchronous (development mode)**

The setting `CELERY_TASK_ALWAYS_EAGER = True` in `config/settings.py` causes all Celery tasks to execute synchronously in the Django request/response cycle. No Celery worker process is needed in development.

**Consequence:** Resume parsing and ranking block the HTTP request until complete. For small uploads (1–5 files) this is acceptable. For bulk uploads of 20+ large files, the request may time out.

**To enable true async (production):**

1. Install and start Redis: `redis-server`
2. Update `backend/.env`:
   ```
   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/0
   ```
3. Remove or set `CELERY_TASK_ALWAYS_EAGER = False` in settings
4. Start the Celery worker: `celery -A config worker --loglevel=info --pool=solo`

**Recommendation:** For production, use Redis as the broker and run at least one Celery worker process. The `--pool=solo` flag is required on Windows due to multiprocessing constraints.

---

## NLP Stack Status

**spaCy: NOT USED**

spaCy was considered during design but removed due to the absence of pre-built Python 3.13 wheels. The project is entirely spaCy-free.

**Current NLP stack (all Python 3.13 compatible):**

| Library | Version Constraint | Role |
|---|---|---|
| NLTK | Any recent | Tokenization, POS tagging, n-gram extraction |
| scikit-learn | ≥ 1.5 (has 3.13 wheels) | TF-IDF vectorizer, cosine similarity fallback |
| sentence-transformers | ≥ 3.x (has 3.13 wheels) | Semantic embeddings (all-MiniLM-L6-v2) |
| faiss-cpu | ≥ 1.9 (has 3.13 wheels) | Vector index; optional, graceful fallback |
| Groq SDK | Any | LLM API client |

**NLTK data dependencies:** `punkt_tab`, `averaged_perceptron_tagger_eng`, `stopwords`, `wordnet`. These are downloaded once on first run via the bootstrap function in `extractor.py`.

---

## Seed Data Command

**Location:** `backend/resumes/management/commands/seed_data.py`  
**Invoked via:** `python manage.py seed_data [--clear]`

### Purpose

Creates a realistic demo dataset without requiring actual resume file uploads or Groq API calls. Useful for onboarding, UI development, and testing the ranking pipeline end-to-end.

### Data created

**5 Jobs** — one per archetype:
- Senior Frontend Developer (required: react, typescript, css, html, javascript)
- Python Backend Developer (required: python, django, postgresql, rest api, docker)
- Machine Learning Engineer (required: python, tensorflow, pytorch, scikit-learn, numpy)
- Data Analyst (required: sql, python, tableau, excel, data analysis)
- Full Stack Developer (required: react, nodejs, python, mongodb, rest api)

**20 CandidateProfiles** — 4 per job archetype, designed with deliberate score variance:
- One strong match (all required skills + preferred skills + senior experience)
- One partial match (2–3 required skills, mid-level experience)
- One wrong-field candidate (similar domain but different stack)
- One entry-level / fresh graduate

**100 RankingResults** — every candidate scored against every job. `rank_position` is assigned per job by descending `total_score`.

### Technical behaviour

- Each candidate gets a `Resume` record with a fake PDF placeholder (`%PDF-1.4 seed-data-placeholder`) stored in `media/resumes/`
- `content_hash` is derived from `email + name` (SHA-256) — ensures idempotency; re-running skips already-created records
- `embedding_vector` is stored as an empty list (`[]`) — semantic search returns no results for seed candidates unless re-embedded
- Ranking uses `compute_total_score()` and `generate_justification()` from `ai_pipeline/ranker.py` directly; Groq is disabled (env var set to empty string) so justifications come from the NLP fallback path
- `extraction_method` is set to `"seed_data"` in the structured profile, distinguishing seed records from real parsed ones

### `--clear` flag

Executes in order: `RankingResult.objects.all().delete()` → `CandidateProfile.objects.all().delete()` → `Resume.objects.all().delete()` → `Job.objects.all().delete()`. Cascades handle related objects. Re-seeds immediately after.

---

## Security Model

### What is protected

| Vector | Control |
|---|---|
| File upload type spoofing | Extension whitelist: `.pdf`, `.docx`, `.jpg`, `.jpeg`, `.png` |
| Oversized uploads | 10 MB per-file cap enforced in view before task dispatch |
| Path traversal | `os.path.basename()` + explicit `..` check on every filename |
| API abuse | DRF throttling: 120/min (anon), 600/min (auth) |
| Cross-origin requests | CORS restricted to `http://localhost:3000` by default; configurable via env |
| Secrets exposure | `.env` in `.gitignore`; all keys via `python-decouple` |

### What is NOT protected

| Gap | Risk | Mitigation |
|---|---|---|
| No authentication | Any user can access all data | Add JWT / session auth before public deployment |
| No HTTPS enforcement | Traffic in cleartext on LAN | Terminate TLS at Nginx / load balancer in production |
| Django `DEBUG=True` in dev | Stack traces exposed | Set `DJANGO_DEBUG=False` and configure `ALLOWED_HOSTS` for production |
| SQLite write contention | Concurrent writes fail under load | Migrate to PostgreSQL for production |

---

## Frontend Architecture

### Routing

All routes are wrapped in the `Layout` component (sidebar + outlet):

```
/                    → redirect to /dashboard
/dashboard           → Dashboard.jsx
/upload              → Upload.jsx
/jobs                → Jobs.jsx
/rankings/:jobId?    → Rankings.jsx
/candidates/:id      → CandidateDetail.jsx
```

### State Management

No global state library (no Redux, Zustand, or Context API for data). All server state is fetched locally in each page component via axios calls in `useEffect` hooks. This is appropriate for the current scale but would benefit from React Query or SWR if the app grows.

### API Client (services/api.js)

Single axios instance with:
- Base URL: `VITE_API_URL` environment variable, falling back to `/api` (Vite proxy in dev)
- 60-second timeout
- FormData multipart support for file uploads with upload progress callback

Four export groups: `resumeApi`, `jobApi`, `candidateApi`, `rankingApi` — each mapping to a backend app's endpoints.

### Styling

Tailwind CSS with a custom primary color palette (blues: 50–900). Custom utility classes defined in `index.css`: `.card`, `.btn-primary`, `.btn-secondary`, `.btn-danger`, `.badge`, `.score-bar`, `.score-fill`.

---

## Configuration Reference

### config/settings.py — Key Settings

| Setting | Value (dev) | Purpose |
|---|---|---|
| `CELERY_TASK_ALWAYS_EAGER` | `True` | Synchronous task execution in dev |
| `CELERY_BROKER_URL` | `memory://` | In-memory broker (dev only) |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | LLM model for all Groq calls |
| `CORS_ALLOWED_ORIGINS` | localhost:3000 | Restrict browser cross-origin access |
| `DEFAULT_THROTTLE_RATES` | 120/min (anon), 600/min (auth) | API rate limiting |
| `DEFAULT_PAGINATION_CLASS` | PageNumberPagination | 20 items per page |
| `MEDIA_ROOT` | `backend/media/` | File upload storage |

### vite.config.js — Key Settings

| Setting | Value | Purpose |
|---|---|---|
| `server.port` | 3000 | Dev server port |
| `server.proxy['/api']` | `http://127.0.0.1:8000` | Proxy to Django in dev |
| `server.proxy['/media']` | `http://127.0.0.1:8000` | Proxy for uploaded file serving |
| `build.outDir` | `dist` | Production build output |
| `build.rollupOptions.manualChunks` | vendor, charts, http | Separate vendor chunks for caching |
