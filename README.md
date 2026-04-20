# Smart Talent Selection Engine

An AI-powered hiring platform that replaces keyword-based applicant tracking with semantic understanding, intent mapping, and explainable candidate ranking.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Tech Stack](#tech-stack)
4. [Setup Instructions](#setup-instructions)
5. [Running the Project](#running-the-project)
6. [Environment Variables](#environment-variables)
7. [Features](#features)
8. [API Reference](#api-reference)
9. [Known Issues & Limitations](#known-issues--limitations)
10. [Future Improvements](#future-improvements)

---

## Project Overview

The Smart Talent Selection Engine is a full-stack web application that automates and enriches the candidate screening process. Recruiters upload resumes in bulk, create job descriptions, and receive AI-ranked candidate shortlists — each with a transparent score breakdown and a two-sentence AI justification.

### Key Features

- Multi-format resume ingestion (PDF, DOCX, JPG, PNG) with SHA-256 duplicate detection
- Three-layer NLP extraction pipeline: Regex → NLTK → Groq LLM (layers are additive)
- Semantic candidate ranking with weighted scoring (Skills 40%, Experience 30%, Projects 20%, Education 10%)
- FAISS-based vector similarity search with numpy cosine fallback
- AI-generated job description improvement suggestions via Groq
- Recruiter feedback loop with shortlisting and hiring decision tracking
- Fully explainable scores — every rank includes matched/missing skills and a justification
- Async resume processing via Celery (synchronous in development — no broker required)
- Admin panel at `/admin/`

---

## Architecture

```
Browser (React + Vite)
    │
    │  /api/* proxied in dev → Django :8000
    ▼
Django REST Framework (Backend)
    ├── resumes/        Upload, parse, store
    ├── jobs/           Job description CRUD + JD suggestions
    ├── candidates/     Structured profiles, feedback, semantic search
    └── ranking/        Scoring engine, async ranking runs
         │
         ├── ai_pipeline/parser.py      PDF / DOCX / OCR image → raw text
         ├── ai_pipeline/extractor.py   3-layer NLP → structured profile JSON
         ├── ai_pipeline/embeddings.py  sentence-transformers + FAISS vector store
         └── ai_pipeline/ranker.py      Weighted scoring + Groq justification
              │
              ├── Groq API (llama-3.1-8b-instant)
              ├── FAISS index  (backend/faiss_index/)
              └── SQLite database  (backend/db.sqlite3)
```

**End-to-end data flow:**

1. Recruiter uploads resumes → files are validated, deduplicated by content hash, stored
2. `parse_resume_task` (Celery) fires per file → text extracted → 3-layer NLP → embedding stored in FAISS
3. Recruiter creates a job description → Groq auto-parses requirements into structured fields
4. Recruiter triggers ranking → `rank_candidates_task` scores all processed candidates, generates justifications, stores ranked results
5. Frontend fetches results and renders score breakdowns, skill comparisons, and AI justifications

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| Frontend | React 18 + Vite 6 + Tailwind CSS | JSX only, no TypeScript |
| Backend | Django 4.2 + Django REST Framework | Python 3.13 compatible |
| AI / NLP | Groq (llama-3.1-8b-instant) + NLTK + scikit-learn | No spaCy — fully Python 3.13 safe |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) + FAISS | numpy cosine fallback if FAISS unavailable |
| Async | Celery — `TASK_ALWAYS_EAGER=True` in dev | Synchronous in dev; Redis broker for production |
| Database | SQLite (dev) | PostgreSQL recommended for production |
| File Parsing | pdfplumber / pypdf (PDF), python-docx (DOCX), pytesseract (images) | Tesseract must be installed separately for images |

---

## Setup Instructions

### Prerequisites

- Python 3.10 – 3.13
- Node.js 18+
- A Groq API key — free at [console.groq.com](https://console.groq.com)
- (Optional) Tesseract OCR for image resumes — [Install guide](https://github.com/UB-Mannheim/tesseract/wiki)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Smart_Talent_Selection_Engine
```

### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux

# Install Python dependencies
pip install -r requirements.txt

# Download required NLTK data (once)
python -c "import nltk; [nltk.download(p, quiet=True) for p in ('punkt_tab', 'averaged_perceptron_tagger_eng', 'stopwords', 'wordnet')]"

# Create and configure environment file
copy .env.example .env       # Windows
cp .env.example .env         # macOS / Linux
# Open .env and add your GROQ_API_KEY

# Apply database migrations
python manage.py makemigrations
python manage.py migrate

# Create an admin account
python manage.py createsuperuser
```

### 3. Frontend Setup

```bash
cd frontend
npm install
# Optional: copy .env.example to .env (proxy works without changes in dev)
```

---

## Running the Project

### Development (3 terminals)

**Terminal 1 — Django backend:**

```bash
cd backend
venv\Scripts\activate
python manage.py runserver
# http://localhost:8000
```

**Terminal 2 — Celery worker** *(optional in dev — tasks run synchronously by default)*:

```bash
cd backend
venv\Scripts\activate
celery -A config worker --loglevel=info --pool=solo
```

**Terminal 3 — React frontend:**

```bash
cd frontend
npm run dev
# http://localhost:3000
```

### Windows One-Click Scripts

Run from the repository root:

| Script | Purpose |
|---|---|
| `start_backend.bat` | Creates venv, migrates DB, starts Django on :8000 |
| `start_celery.bat` | Starts Celery worker |
| `start_frontend.bat` | Installs npm deps, starts Vite dev server on :3000 |

### Production Build (Frontend)

```bash
cd frontend
npm run build      # Output: frontend/dist/
npm run preview    # Preview at http://localhost:3000
```

Serve `frontend/dist/` with Nginx, Caddy, or a CDN. Set `VITE_API_URL` to your production backend URL.

---

## Environment Variables

### Backend — `backend/.env`

```env
GROQ_API_KEY=your_groq_api_key_here        # Required for LLM extraction and JD suggestions
DJANGO_SECRET_KEY=change-this-in-production
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Production only:
# CELERY_BROKER_URL=redis://localhost:6379/0
# CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Frontend — `frontend/.env`

```env
# Leave empty to use Vite's built-in proxy (/api → http://127.0.0.1:8000)
VITE_API_URL=

# Production only — set to deployed backend URL:
# VITE_API_URL=https://api.yourdomain.com
```

All frontend variables **must** be prefixed with `VITE_` to be accessible in the browser.

---

## Features

### Resume Management

- Drag-and-drop bulk upload (PDF, DOCX, JPG, PNG — up to 10 MB each)
- SHA-256 duplicate detection — duplicates are flagged without re-storing
- Batch tagging by job role for later filtering
- Real-time status tracking: `pending` → `processing` → `done` / `error`
- Manual re-parse option for failed files

### AI Parsing Pipeline

- **Layer 1 (Regex):** Skills, experience years, education, contact info
- **Layer 2 (NLTK):** N-gram skill detection, POS-based name extraction, TF-IDF keywords
- **Layer 3 (Groq LLM):** Structured JSON — role history, certifications, 2-sentence summary
- All three layers are additive; results are merged into a single profile
- 165+ canonical skills with synonym ontology and 8-domain hierarchy

### Candidate Ranking

- Triggers via "Run Ranking" on any job
- Scoring: Skills (40%) + Experience (30%) + Projects (20%) + Education (10%)
- Per-component score breakdown on every result
- AI-generated 2-sentence justification per candidate (Groq)
- Multi-skill AND filter and minimum score threshold filter

### Semantic Search

- Query by natural language text
- sentence-transformers (384-dim) → FAISS inner-product search
- numpy cosine fallback when FAISS is unavailable

### Job Description Tools

- Structured JD storage: required skills, preferred skills, min experience, education, department
- Auto-parse JD on creation via Groq
- "Suggest Improvements" — Groq-powered JD optimization

### Candidate Detail View

- 6-tab profile: Overview, Resume, Skills, Experience, Comparison, Feedback
- Side-by-side skill gap analysis vs. selected job
- Experience timeline and project portfolio
- Inline PDF / image resume viewer
- Recruiter feedback: Shortlisted, Interview, Hired, Rejected

### Dashboard

- Live stats: total resumes, processed, active jobs, queue depth
- Status distribution chart and resumes-by-role bar chart
- Quick access to top-ranked candidates per active job

---

## Seed Data

The project ships with a management command that populates the database with realistic demo data — no real resume files required. Use this to explore the full UI immediately after setup.

### What gets created

| Data | Count | Details |
|---|---|---|
| Jobs | 5 | Senior Frontend Developer, Python Backend Developer, Machine Learning Engineer, Data Analyst, Full Stack Developer |
| Candidates | 20 | 4 per job archetype with varying skill coverage (strong match → partial → wrong field → entry level) |
| Ranking results | 100 | All 20 candidates scored against all 5 jobs |

Justifications are generated using the NLP fallback — no Groq API key needed for seeding.

### Commands

```bash
cd backend
venv\Scripts\activate          # Windows — activate virtual environment

# Load seed data (safe to run multiple times — skips existing records)
python manage.py seed_data

# Wipe all existing data first, then re-seed
python manage.py seed_data --clear
```

### Verifying the seed

After running, open [http://localhost:3000](http://localhost:3000):

1. **Jobs page** — 5 jobs should be listed
2. **Rankings page** — select any job from the dropdown; 20 ranked candidates appear immediately
3. **Candidate detail** — click any card to see the full profile, skills, experience, and comparison tab

### Resetting to a clean state

```bash
python manage.py seed_data --clear   # wipes all jobs, candidates, and rankings, then re-seeds
```

To wipe everything without re-seeding, use the Django shell or admin panel at `/admin/`.

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/resumes/upload/` | POST | Bulk upload — multipart `files[]` + `job_role` |
| `/api/resumes/` | GET | List resumes (filter: `status`, `job_role`) |
| `/api/resumes/stats/` | GET | Aggregate counts by status and role |
| `/api/resumes/{id}/reparse/` | POST | Re-trigger parsing on a resume |
| `/api/jobs/` | GET / POST | List / create jobs |
| `/api/jobs/{id}/` | GET / PATCH / DELETE | Single job operations |
| `/api/jobs/{id}/run-ranking/` | POST | Trigger async ranking for a job |
| `/api/jobs/{id}/suggest-jd/` | GET | Groq-powered JD improvement suggestions |
| `/api/candidates/` | GET | List candidates (filter: `is_shortlisted`, `job_role`) |
| `/api/candidates/{id}/` | GET / DELETE | Single candidate operations |
| `/api/candidates/{id}/vs-jd/` | GET | Skill gap comparison vs. a job (`?job_id=`) |
| `/api/candidates/{id}/feedback/` | POST | Submit recruiter hiring decision |
| `/api/candidates/search/` | GET | Semantic FAISS search (`?q=`) |
| `/api/ranking/results/` | GET | Ranked results (filter: `job_id`, `min_score`, `skills`) |
| `/api/ranking/runs/` | GET | Ranking run history |
| `/api/ranking/runs/quick-rank/` | POST | Synchronous rank — body: `jd_text`, `job_id`, `limit` |

Rate limits: 120 req/min (anonymous), 600 req/min (authenticated).

---

## Known Issues & Limitations

| Issue | Status | Notes |
|---|---|---|
| Celery async in dev | By design | `CELERY_TASK_ALWAYS_EAGER = True` — tasks execute synchronously. For production async, start a Celery worker and set a Redis broker URL. |
| spaCy not used | Resolved | Replaced with NLTK + scikit-learn for Python 3.13 compatibility. spaCy is not a dependency. |
| FAISS optional | Handled | Automatically falls back to numpy cosine similarity if `faiss-cpu` is not installed. |
| No authentication | Known gap | No login/auth system. Do not expose to the public internet without adding auth. |
| Groq dependency | API-dependent | Parsing degrades to regex + NLTK only if `GROQ_API_KEY` is missing or invalid. |
| SQLite in production | Not recommended | SQLite has write concurrency limits. Use PostgreSQL for production. |
| Candidate name "Candidate #N" | Expected | Occurs when the resume has no extractable name. All data is still present. |
| Tesseract optional | For image resumes | Image parsing requires Tesseract OCR installed on the host system. |

---

## Future Improvements

- JWT or OAuth2 authentication with role-based access (recruiter vs. admin)
- PostgreSQL migration with connection pooling
- Redis broker for true production Celery async
- Resume anonymization and bias-reduction preprocessing
- Batch export of ranked results to CSV / Excel
- Webhook notifications on ranking completion
- Side-by-side multi-candidate comparison view
- Resume version history (track re-parsed profiles over time)
- End-to-end test suite (Playwright for frontend, pytest integration tests for backend)
- Confidence score display in the ranking UI
