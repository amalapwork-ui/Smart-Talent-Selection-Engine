# Operation Manual — Smart Talent Selection Engine

This guide walks through every step of using the platform — from first launch to hiring decisions — in plain language, with no assumed technical knowledge.

---

## Before You Begin

Make sure the project is set up and running. If you have not set it up yet, follow the [Setup Instructions in the README](README.md#setup-instructions) first.

You need three things running at the same time:

1. The **Django backend** (the server that handles data and AI)
2. The **React frontend** (the interface you use in your browser)
3. (Optional) A **Celery worker** (for processing resumes in the background)

Once all three are running, open your browser and go to:
**http://localhost:3000**

---

## Understanding the Interface

The screen is divided into two parts:

- **Left sidebar:** Navigation menu with four sections — Dashboard, Upload, Jobs, Rankings
- **Main area:** Changes depending on which section you are in

On mobile or small screens, the sidebar collapses. Tap the menu icon at the top-left to open it.

---

## The Full Workflow

```
Upload Resumes → Wait for Parsing → Create a Job → Run Ranking → View Results → Review Candidates → Give Feedback
```

Each step is explained below.

---

## Step 1 — Upload Resumes

**Where:** Click **Upload** in the left sidebar.

This is where you bring candidates into the system. The platform accepts resumes in these formats: PDF, Word (DOCX), and images (JPG, PNG). Each file must be under 10 MB.

### How to upload

1. Type a **Job Role / Batch Tag** in the text field at the top (for example: *Backend Developer* or *Q1 2026 Batch*). This tag groups your resumes for filtering later — it does not have to match an exact job title.

2. In the upload area, either:
   - Drag and drop your files directly onto the area, or
   - Click the area to open a file browser and select files

3. You will see a list of the selected files with their names and sizes. Review the list.

4. Click the **Upload** button.

### What happens next

After upload, you will see a status table below the upload area. Each row is one resume, and it will show one of these statuses:

| Status | Meaning |
|---|---|
| **Pending** | Waiting in the queue to be processed |
| **Processing** | The AI is currently reading and extracting data |
| **Done** | Parsing completed successfully |
| **Error** | Something went wrong — see the error message |

The page checks the status automatically every few seconds. You do not need to refresh.

### If a resume shows Error

Click the **Retry** button on that row. This re-submits the file for parsing. If it keeps failing, the file may be corrupted, password-protected, or contain only scanned images without OCR support.

### Duplicate detection

If you upload a file that was already uploaded (even with a different filename), the system detects it automatically using a digital fingerprint of the file content. The duplicate is not stored again — it is flagged in the upload result.

### Deleting a resume

Click the **trash icon** on any row to remove a resume from the system. This also removes the associated candidate profile if one was created.

---

## Step 2 — Create a Job Description

**Where:** Click **Jobs** in the left sidebar, then click **+ New Job**.

Before you can rank candidates, you need at least one job in the system.

### Filling in the job form

| Field | What to enter | Required? |
|---|---|---|
| **Title** | The job title, e.g. *Senior Python Developer* | Yes |
| **Department** | Team or department, e.g. *Engineering* | No |
| **Location** | e.g. *Remote*, *New York* | No |
| **Employment Type** | Full Time / Part Time / Contract / Internship | No |
| **Min Experience (years)** | Minimum years of experience required | No |
| **Education Required** | e.g. *Bachelor's in Computer Science* | No |
| **Required Skills** | Comma-separated list, e.g. *Python, Django, REST APIs* | No |
| **Preferred Skills** | Nice-to-have skills, e.g. *Docker, AWS* | No |
| **Description** | Paste the full job description text | Yes |

The more detail you provide, especially in Required Skills and Description, the more accurate the ranking will be.

### What happens when you save

The system sends your job description to the AI, which reads it and extracts a structured list of requirements (required skills, experience level, education, responsibilities). This takes a few seconds. You will see a toast notification when it is saved.

### Editing a job

Click the **Edit** (pencil) icon on any job card. Make your changes and save. The AI will re-parse the description.

### Deleting a job

Click the **Delete** (trash) icon on the job card. This removes the job and all ranking results associated with it. Candidate profiles themselves are not deleted.

### AI Improvement Suggestions

On any job card, click **Suggest Improvements**. The AI reads your job description and gives you feedback on how to make it clearer and more attractive to candidates. The suggestions appear in an amber panel below the job card.

If this button gives an error, your Groq API key may be missing or invalid. Check `backend/.env`.

---

## Step 3 — Run Ranking

**Where:** From the **Jobs** page, click **Run Ranking** on any job card.  
Or go to **Rankings**, select a job, and click **Run Ranking** there.

This is where the AI scores every processed candidate against the job requirements and puts them in order.

### What the AI considers

The final score (0–100) is made up of four parts:

| Component | Weight | What it measures |
|---|---|---|
| **Skill Match** | 40% | How many required and preferred skills the candidate has |
| **Experience Depth** | 30% | Years of experience vs. the minimum you set |
| **Project Relevance** | 20% | How closely the candidate's projects relate to your tech stack |
| **Education** | 10% | Degree level and relevant certifications |

### How long does it take?

For 10–20 candidates, ranking typically completes in under 30 seconds. For larger batches, it may take 1–2 minutes because the AI generates a short justification for every candidate.

A toast notification will appear when ranking is done. The results load automatically.

---

## Step 4 — View & Filter Rankings

**Where:** Click **Rankings** in the left sidebar.

### Selecting a job

Use the **Select a job** dropdown at the top to choose which job's results to view.

If no results appear, either ranking has not been run yet, or no candidates have been processed.

### Filtering results

**Minimum Score filter:**
Type a number (0–100) in the **Min Score** field. Only candidates with a total score at or above that number will be shown.

**Skill filter:**
Type a skill name in the skill filter box and press Enter or comma. A chip (small tag) appears. Add as many skills as you want. Only candidates who have **all** of the selected skills are shown.

To remove a skill filter, click the **×** on its chip.

### Reading a candidate card

Each card shows:

- **Rank badge** — #1, #2, #3 (gold, silver, bronze for top 3)
- **Name** — extracted from the resume (or Candidate #N if no name was found)
- **Experience years** — from the resume
- **Total score** — large number on the right
- **Score bars** — four mini bars showing Skills, Experience, Projects, Education scores
- **Skills** — top 6 skill tags from the candidate's profile
- **Justification** — a one-to-two sentence AI explanation of why this candidate was ranked here

Click anywhere on a card to open the full candidate profile.

### Deleting a candidate from rankings

Hover over any card and a **trash icon** appears. Click it and confirm the dialog. This removes the candidate profile and all their ranking results from the system. The original resume file is also deleted.

---

## Step 5 — Open a Candidate's Full Profile

**Where:** Click any candidate card in Rankings.

The candidate detail page has six tabs:

### Overview Tab

- Quick stats: total experience years, number of skills found, number of projects, certifications, and which AI method extracted the profile
- Work experience and education summary
- Score breakdown (if a job is selected in the comparison selector at the top)
- Profile summary — a two-sentence AI-generated description of the candidate

### Resume Tab

- Shows the original resume file inside the page
- PDF files open as an embedded viewer
- Image files (JPG, PNG) display directly
- Other formats (DOCX) offer a download button

### Skills Tab

- All extracted skills organized by category (Backend, Frontend, Database, DevOps, Machine Learning, Mobile, Security, Testing)
- A flat list of all skills below the categories

### Experience Tab

- Work history timeline: each role with company name, duration, and description
- Projects section: project names with their tech stack as tags

### Comparison Tab

This tab only shows content after you select a job from the **Compare with job** dropdown at the top of the page.

It shows three lists:
- **Matching skills** (green checkmarks) — skills the candidate has that your job requires
- **Missing skills** (red X) — required skills the candidate does not have
- **Extra skills** (gray) — skills the candidate has that are not in the job requirements

The score breakdown (four bars) also appears here.

### Feedback Tab

This is where you record your hiring decision.

1. Select the job from the dropdown at the top of the page
2. Go to the Feedback tab
3. Choose a **Decision**:
   - **Shortlisted** — promising candidate, keep reviewing
   - **Called for Interview** — moving to interview stage
   - **Hired** — candidate was hired
   - **Rejected** — not proceeding

4. Add optional **Notes** (e.g., "Strong Python skills, weak on system design")
5. Click **Submit Feedback**

The decision badge appears in the candidate's header on this page. Shortlisted, Interview, and Hired candidates are marked with `is_shortlisted = true`, which enables filtering in the candidate list.

---

## Step 6 — Using the Dashboard

**Where:** Click **Dashboard** in the left sidebar.

The dashboard gives you a high-level view of the hiring pipeline at a glance.

### What you see

**Stat cards (top row):**
- **Total Resumes** — all resumes in the system
- **Processed** — resumes that completed parsing
- **Active Jobs** — jobs with `is_active = true`
- **In Queue** — resumes still pending or processing

**Charts (middle row):**
- **Resume Status Distribution** — pie chart showing done / processing / pending / error
- **Resumes by Role** — bar chart showing the top 6 batch tags by volume

**Bottom sections:**
- **Active Jobs** — clickable cards for each open job; click to go to its rankings
- **Top Ranked Candidates** — top 5 candidates from the first active job; click any to open their profile

### Refreshing data

Click the **Refresh** button (circular arrow icon) at the top right to reload all dashboard data.

---

## Common Problems and Fixes

| Problem | Likely Cause | What to do |
|---|---|---|
| Resume stuck at "Pending" for more than a minute | Celery worker is not running (in async mode) | Start the Celery worker, or set `CELERY_TASK_ALWAYS_EAGER=True` in `backend/.env` |
| Resume shows "Error" | File is corrupted, password-protected, or unsupported | Click **Retry**. If it still fails, try a different file format |
| "Suggest Improvements" shows error | Missing or invalid Groq API key | Add `GROQ_API_KEY` to `backend/.env` and restart the backend |
| Rankings page shows no results | Ranking has not been run yet | Click **Run Ranking** on the Jobs page or Rankings page |
| Candidate shows "Candidate #1" instead of a name | The resume did not contain a recognizable name | Normal — all data is still present; click into the profile |
| Score of 0 for all candidates | Job has no required skills or description | Edit the job and add required skills and a detailed description |
| Skill filter returns no results | Skill may be normalized (synonym mapped) | Try the canonical form, e.g. `sql` instead of `postgresql` |
| CORS error in browser | Frontend URL is not in the backend's allowed list | Add your URL to `CORS_ALLOWED_ORIGINS` in `backend/.env` |
| `no such table` error | Migrations not applied | Run `python manage.py migrate` in the backend folder |

---

## Using Seed Data (Quick Demo Setup)

If you want to explore the platform immediately — without uploading real resumes — use the built-in seed data command. It creates 5 jobs and 20 candidates with pre-computed rankings so every page works right away.

### What the seed data contains

| Category | Count | What you get |
|---|---|---|
| Jobs | 5 | Frontend, Backend, ML Engineer, Data Analyst, Full Stack |
| Candidates | 20 | 4 per job type — ranging from strong matches to entry-level |
| Rankings | 100 | All candidates scored against all jobs |

The candidates have realistic names, skills, work histories, and projects. You can click through every page and tab as if working with real data.

No Groq API key is needed to load seed data. Justifications are generated using the built-in NLP engine.

### Loading the seed data

Make sure the backend is set up and migrations have been applied (see the README Setup section). Then run:

```bash
cd backend
venv\Scripts\activate          # Windows
python manage.py seed_data
```

You will see output like:

```
Creating 5 jobs...
  + Job: Senior Frontend Developer
  + Job: Python Backend Developer
  ...
Creating 20 candidates...
  + Candidate: Aanya Sharma
  + Candidate: Arjun Patel
  ...
Computing rankings (no LLM — NLP fallback)...
  [OK] Senior Frontend Developer: 20 candidates ranked
  ...
Seed complete: 5 jobs, 20 candidates, 100 ranking results.
```

### Verifying the seed worked

1. Open [http://localhost:3000](http://localhost:3000) in your browser
2. Go to **Rankings** → select any job from the dropdown
3. You should see 20 ranked candidates with scores, skill bars, and justifications
4. Click any candidate to open their full profile — all 6 tabs will have content

### Re-running and resetting

The seed command is **safe to run multiple times**. It detects existing records and skips them, so running it again will not create duplicates.

To wipe all data and start fresh:

```bash
python manage.py seed_data --clear
```

This deletes all jobs, candidates, and ranking results, then immediately re-seeds with clean data.

To wipe all data without re-seeding, use the Django admin panel at `http://localhost:8000/admin/`.

### Differences from real data

Seed candidates have a few intentional differences from real uploaded resumes:

- Their resume files are placeholder PDFs — the **Resume tab** in candidate detail will not show a readable document
- The **extraction method** shows `seed_data` instead of the normal AI layer names
- Semantic search (`/api/candidates/search/`) will not match seed candidates because no embedding vectors were computed

Everything else — rankings, score breakdowns, skill comparison, feedback — works identically to real data.

---

## Admin Panel

The Django admin panel is available at:
**http://localhost:8000/admin/**

Log in with the superuser account you created during setup. From there you can view, edit, or delete any record directly in the database — useful for debugging or manual corrections.

---

## Data Privacy Notes

- No authentication is implemented. Anyone who can reach the app can see all candidates and data.
- Do not upload real personally identifiable information (PII) to a development instance that is accessible on a shared network.
- Before deploying to a production environment, add authentication and enable HTTPS.
