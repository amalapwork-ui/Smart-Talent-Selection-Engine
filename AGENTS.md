# Repository Guidelines

## Project Structure & Module Organization

Full-stack AI hiring platform. The backend is Django 4.2 with five apps; the frontend is React 18 + Vite 6.

```
backend/
  config/         # Django settings, URL root, Celery app
  ai_pipeline/    # parser.py → extractor.py → embeddings.py → ranker.py (pipeline order matters)
  resumes/        # Upload, duplicate detection (SHA-256), async parsing tasks
  jobs/           # Job description management + JD suggestion endpoint
  candidates/     # Structured profiles built from parsed resumes
  ranking/        # Scoring engine + async ranking tasks + results API
frontend/
  src/
    pages/        # Dashboard, Upload, Jobs, Rankings, CandidateDetail
    components/   # Layout, ScoreBreakdown, CandidateCard, etc.
    services/api.js  # Axios client — reads VITE_API_URL or falls back to Vite proxy
```

**Key non-obvious wiring:** Vite dev server proxies `/api` and `/media` to `http://127.0.0.1:8000` — no CORS headers needed during development. In production, set `VITE_API_URL` to the deployed backend URL.

**AI pipeline flow:** `parser.py` reads PDF/DOCX/images → `extractor.py` runs 3 additive layers (regex → NLTK → Groq LLM, results merged) → `embeddings.py` stores sentence-transformer vectors in FAISS → `ranker.py` scores with weights: Skills 40%, Experience 30%, Projects 20%, Education 10%.

**Celery broker:** `django://` (Django DB) for local dev — no Redis required. Set `CELERY_BROKER_URL=redis://localhost:6379/0` in `backend/.env` for production.

## Build, Test, and Development Commands

```bash
# Backend
cd backend
python -m venv venv && venv\Scripts\activate   # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver                      # http://localhost:8000

# Celery worker (separate terminal)
celery -A config worker --loglevel=info --pool=solo

# Frontend
cd frontend
npm install
npm run dev        # http://localhost:3000
npm run build      # outputs to frontend/dist/
npm run preview    # preview production build

# Windows shortcuts (repo root)
start_backend.bat / start_celery.bat / start_frontend.bat
```

## Testing Guidelines

Backend uses **pytest-django**. Run from `backend/`:

```bash
cd backend
pytest                        # all tests
pytest resumes/tests.py       # single app
pytest -k test_upload         # single test by name
```

`pytest.ini` sets `DJANGO_SETTINGS_MODULE = config.settings` and `-v --tb=short`. `conftest.py` disables Celery eager mode so tasks must be mocked in unit tests. No frontend test suite is configured.

## Environment Variables

Copy `.env.example` (frontend) and create `backend/.env`:

| Variable | Required | Notes |
|---|---|---|
| `GROQ_API_KEY` | Yes | LLM extraction and JD suggestions |
| `DJANGO_SECRET_KEY` | Yes | Change in production |
| `CELERY_BROKER_URL` | No | Defaults to `django://`; use `redis://` in prod |
| `VITE_API_URL` | No | Leave empty in dev; set to backend URL in prod |
