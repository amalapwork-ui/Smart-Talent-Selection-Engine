"""
Seed data management command.

Creates realistic jobs, candidate profiles, and ranking results
without requiring actual resume files to be processed.

Usage:
    python manage.py seed_data           # creates seed data
    python manage.py seed_data --clear   # wipe seed data first
"""
import hashlib
import random
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile


# ---------------------------------------------------------------------------
# Seed definitions
# ---------------------------------------------------------------------------

JOBS = [
    {
        "title": "Senior Frontend Developer",
        "description": (
            "We are seeking a Senior Frontend Developer to build responsive, performant web "
            "applications using React and TypeScript. You will collaborate with designers and "
            "backend teams to deliver pixel-perfect UIs. 3+ years of React experience required."
        ),
        "required_skills": ["react", "typescript", "css", "html", "javascript"],
        "preferred_skills": ["graphql", "redux", "jest", "webpack", "vite"],
        "min_experience_years": 3,
        "education_required": "Bachelor's degree in Computer Science or equivalent",
        "department": "Engineering",
        "location": "Bangalore",
        "employment_type": "full_time",
    },
    {
        "title": "Python Backend Developer",
        "description": (
            "Join our backend team to design and implement scalable REST APIs using Django and "
            "Django REST Framework. You will work with PostgreSQL, Redis, and Docker to build "
            "reliable microservices. 2+ years of Python/Django experience required."
        ),
        "required_skills": ["python", "django", "postgresql", "rest api", "docker"],
        "preferred_skills": ["redis", "celery", "aws", "kubernetes", "fastapi"],
        "min_experience_years": 2,
        "education_required": "B.Tech or equivalent",
        "department": "Backend Engineering",
        "location": "Remote",
        "employment_type": "full_time",
    },
    {
        "title": "Machine Learning Engineer",
        "description": (
            "We are building production ML systems and need an ML Engineer experienced with "
            "deep learning frameworks. You will design, train, and deploy models using PyTorch "
            "and TensorFlow. Strong Python skills and 3+ years ML experience required."
        ),
        "required_skills": ["python", "tensorflow", "pytorch", "scikit-learn", "numpy"],
        "preferred_skills": ["mlflow", "spark", "kubernetes", "docker", "pandas"],
        "min_experience_years": 3,
        "education_required": "Master's or Ph.D in ML/CS preferred",
        "department": "AI Research",
        "location": "Hyderabad",
        "employment_type": "full_time",
    },
    {
        "title": "Data Analyst",
        "description": (
            "We are looking for a Data Analyst to turn business data into actionable insights. "
            "You will write SQL queries, build Tableau dashboards, and work with business "
            "stakeholders. Experience with Python for data manipulation is a plus."
        ),
        "required_skills": ["sql", "python", "tableau", "excel", "data analysis"],
        "preferred_skills": ["power bi", "r", "spark", "pandas"],
        "min_experience_years": 1,
        "education_required": "Bachelor's degree in Statistics, Math, or CS",
        "department": "Data & Analytics",
        "location": "Mumbai",
        "employment_type": "full_time",
    },
    {
        "title": "Full Stack Developer",
        "description": (
            "We need a Full Stack Developer comfortable building end-to-end features across "
            "React frontends and Python/Node.js backends. Experience with MongoDB and REST "
            "API design is essential. 2+ years full-stack experience required."
        ),
        "required_skills": ["react", "nodejs", "python", "mongodb", "rest api"],
        "preferred_skills": ["docker", "aws", "graphql", "typescript"],
        "min_experience_years": 2,
        "education_required": "B.Tech or equivalent",
        "department": "Product Engineering",
        "location": "Pune",
        "employment_type": "full_time",
    },
]

# 20 candidate profiles — 4 per job archetype with varying skill coverage
CANDIDATES = [
    # ── Frontend candidates (for Job 0 — Senior Frontend Developer) ──
    {
        "name": "Aanya Sharma",
        "email": "aanya.sharma@example.com",
        "phone": "+91-9876543201",
        "job_role": "Frontend Developer",
        "skills": ["react", "typescript", "css", "html", "javascript", "redux", "jest", "webpack"],
        "experience_years": 5,
        "roles": [
            {"title": "Senior Frontend Engineer", "company": "Flipkart", "years": 3},
            {"title": "Frontend Developer", "company": "Startups.io", "years": 2},
        ],
        "education": [{"degree": "B.Tech Computer Science", "institution": "IIT Delhi", "year": "2019"}],
        "certifications": ["AWS Certified Developer", "React Advanced Certification"],
        "projects": [
            {
                "name": "E-Commerce Dashboard",
                "description": "Built high-performance React dashboard with TypeScript and Redux",
                "tech_stack": ["react", "typescript", "redux", "css"],
            },
            {
                "name": "Design System",
                "description": "Created reusable component library with Jest tests",
                "tech_stack": ["react", "typescript", "jest", "webpack"],
            },
        ],
        "summary": "Senior frontend engineer with 5 years building scalable React applications.",
    },
    {
        "name": "Rohan Mehta",
        "email": "rohan.mehta@example.com",
        "phone": "+91-9876543202",
        "job_role": "Frontend Developer",
        "skills": ["react", "javascript", "css", "html"],
        "experience_years": 2,
        "roles": [{"title": "Frontend Developer", "company": "TechCorp", "years": 2}],
        "education": [{"degree": "B.Sc Computer Science", "institution": "Delhi University", "year": "2022"}],
        "certifications": [],
        "projects": [
            {
                "name": "Portfolio App",
                "description": "React single-page application with CSS animations",
                "tech_stack": ["react", "javascript", "css"],
            }
        ],
        "summary": "Frontend developer with 2 years of React and JavaScript experience.",
    },
    {
        "name": "Priya Nair",
        "email": "priya.nair@example.com",
        "phone": "+91-9876543203",
        "job_role": "Frontend Developer",
        "skills": ["angular", "vue", "javascript", "css", "html"],
        "experience_years": 3,
        "roles": [{"title": "UI Developer", "company": "InfoSys", "years": 3}],
        "education": [{"degree": "B.Tech", "institution": "VIT University", "year": "2021"}],
        "certifications": [],
        "projects": [
            {
                "name": "Admin Panel",
                "description": "Angular admin dashboard with complex data grids",
                "tech_stack": ["angular", "javascript", "css"],
            }
        ],
        "summary": "UI developer experienced with Angular and Vue, transitioning to React.",
    },
    {
        "name": "Dev Kapoor",
        "email": "dev.kapoor@example.com",
        "phone": "+91-9876543204",
        "job_role": "Backend Developer",
        "skills": ["python", "django", "sql"],
        "experience_years": 1,
        "roles": [{"title": "Junior Developer", "company": "Startup Inc", "years": 1}],
        "education": [{"degree": "Diploma in CS", "institution": "NIIT", "year": "2023"}],
        "certifications": [],
        "projects": [],
        "summary": "Junior backend developer with basic Python and Django skills.",
    },

    # ── Backend candidates (for Job 1 — Python Backend Developer) ──
    {
        "name": "Arjun Patel",
        "email": "arjun.patel@example.com",
        "phone": "+91-9876543205",
        "job_role": "Backend Developer",
        "skills": ["python", "django", "postgresql", "rest api", "docker", "redis", "celery"],
        "experience_years": 4,
        "roles": [
            {"title": "Backend Engineer", "company": "Razorpay", "years": 2},
            {"title": "Python Developer", "company": "Ola", "years": 2},
        ],
        "education": [{"degree": "B.Tech Computer Science", "institution": "BITS Pilani", "year": "2020"}],
        "certifications": ["AWS Solutions Architect", "Docker Certified Associate"],
        "projects": [
            {
                "name": "Payment Microservice",
                "description": "Django REST API for payment processing with PostgreSQL and Redis cache",
                "tech_stack": ["python", "django", "postgresql", "redis", "docker"],
            },
            {
                "name": "Celery Task Queue",
                "description": "Async task processing system with Celery and Django",
                "tech_stack": ["celery", "django", "python", "redis"],
            },
        ],
        "summary": "Backend engineer with 4 years building Django REST APIs at scale.",
    },
    {
        "name": "Sneha Iyer",
        "email": "sneha.iyer@example.com",
        "phone": "+91-9876543206",
        "job_role": "Backend Developer",
        "skills": ["python", "django", "mysql", "rest api"],
        "experience_years": 2,
        "roles": [{"title": "Software Developer", "company": "HCL", "years": 2}],
        "education": [{"degree": "M.Tech Software Engineering", "institution": "NIT Trichy", "year": "2022"}],
        "certifications": [],
        "projects": [
            {
                "name": "Inventory Management API",
                "description": "REST API for inventory management using Django and MySQL",
                "tech_stack": ["python", "django", "mysql"],
            }
        ],
        "summary": "Software developer with Django and REST API experience.",
    },
    {
        "name": "Kiran Reddy",
        "email": "kiran.reddy@example.com",
        "phone": "+91-9876543207",
        "job_role": "Backend Developer",
        "skills": ["java", "spring boot", "postgresql", "docker"],
        "experience_years": 3,
        "roles": [{"title": "Java Developer", "company": "Wipro", "years": 3}],
        "education": [{"degree": "B.Tech", "institution": "Osmania University", "year": "2021"}],
        "certifications": ["Oracle Java Certified"],
        "projects": [
            {
                "name": "Banking API",
                "description": "Spring Boot REST API for banking transactions",
                "tech_stack": ["java", "spring boot", "postgresql", "docker"],
            }
        ],
        "summary": "Java backend developer with Spring Boot and Docker experience.",
    },
    {
        "name": "Meera Pillai",
        "email": "meera.pillai@example.com",
        "phone": "+91-9876543208",
        "job_role": "Frontend Developer",
        "skills": ["react", "html", "css"],
        "experience_years": 1,
        "roles": [{"title": "Intern", "company": "Accenture", "years": 1}],
        "education": [{"degree": "B.Tech Computer Science", "institution": "Amrita University", "year": "2023"}],
        "certifications": [],
        "projects": [],
        "summary": "Recent graduate with basic frontend skills.",
    },

    # ── ML candidates (for Job 2 — Machine Learning Engineer) ──
    {
        "name": "Dr. Vikram Singh",
        "email": "vikram.singh@example.com",
        "phone": "+91-9876543209",
        "job_role": "ML Engineer",
        "skills": ["python", "tensorflow", "pytorch", "scikit-learn", "numpy", "pandas", "mlflow", "docker"],
        "experience_years": 6,
        "roles": [
            {"title": "Senior ML Engineer", "company": "Google India", "years": 3},
            {"title": "Research Scientist", "company": "IISc", "years": 3},
        ],
        "education": [
            {"degree": "Ph.D Machine Learning", "institution": "IISc Bangalore", "year": "2018"},
            {"degree": "M.Tech", "institution": "IIT Bombay", "year": "2014"},
        ],
        "certifications": ["TensorFlow Developer Certificate", "AWS ML Specialty"],
        "projects": [
            {
                "name": "NLP Classification System",
                "description": "BERT-based text classification using PyTorch and TensorFlow serving",
                "tech_stack": ["pytorch", "tensorflow", "python", "numpy"],
            },
            {
                "name": "MLOps Pipeline",
                "description": "End-to-end ML pipeline with MLflow tracking and Docker deployment",
                "tech_stack": ["mlflow", "docker", "python", "scikit-learn"],
            },
        ],
        "summary": "Ph.D ML researcher with 6 years of industry and academic experience.",
    },
    {
        "name": "Anita Gupta",
        "email": "anita.gupta@example.com",
        "phone": "+91-9876543210",
        "job_role": "ML Engineer",
        "skills": ["python", "scikit-learn", "tensorflow", "pandas", "numpy"],
        "experience_years": 3,
        "roles": [{"title": "ML Engineer", "company": "Swiggy", "years": 3}],
        "education": [{"degree": "M.Tech AI", "institution": "IIIT Hyderabad", "year": "2021"}],
        "certifications": ["Deep Learning Specialization (Coursera)"],
        "projects": [
            {
                "name": "Recommendation Engine",
                "description": "Collaborative filtering system using scikit-learn and TensorFlow",
                "tech_stack": ["python", "scikit-learn", "tensorflow", "pandas"],
            }
        ],
        "summary": "ML engineer specializing in recommendation systems and NLP.",
    },
    {
        "name": "Rahul Joshi",
        "email": "rahul.joshi@example.com",
        "phone": "+91-9876543211",
        "job_role": "ML Engineer",
        "skills": ["python", "pandas", "numpy", "matplotlib"],
        "experience_years": 1,
        "roles": [{"title": "Data Scientist Intern", "company": "Analytics Firm", "years": 1}],
        "education": [{"degree": "B.Tech", "institution": "MNIT Jaipur", "year": "2023"}],
        "certifications": [],
        "projects": [
            {
                "name": "Sales Forecasting",
                "description": "Time series analysis using pandas and matplotlib",
                "tech_stack": ["python", "pandas", "numpy"],
            }
        ],
        "summary": "Entry-level data scientist with Python data analysis skills.",
    },
    {
        "name": "Pooja Agarwal",
        "email": "pooja.agarwal@example.com",
        "phone": "+91-9876543212",
        "job_role": "Data Analyst",
        "skills": ["sql", "excel", "tableau", "python"],
        "experience_years": 2,
        "roles": [{"title": "Data Analyst", "company": "Myntra", "years": 2}],
        "education": [{"degree": "B.Sc Statistics", "institution": "Lady Shri Ram College", "year": "2022"}],
        "certifications": ["Tableau Desktop Certified"],
        "projects": [
            {
                "name": "Sales Dashboard",
                "description": "Tableau dashboard for executive sales reporting",
                "tech_stack": ["tableau", "sql", "excel"],
            }
        ],
        "summary": "Data analyst skilled in Tableau dashboards and SQL reporting.",
    },

    # ── Data Analyst candidates (for Job 3 — Data Analyst) ──
    {
        "name": "Siddharth Nair",
        "email": "siddharth.nair@example.com",
        "phone": "+91-9876543213",
        "job_role": "Data Analyst",
        "skills": ["sql", "python", "tableau", "excel", "data analysis", "power bi", "r"],
        "experience_years": 3,
        "roles": [
            {"title": "Senior Data Analyst", "company": "Zomato", "years": 2},
            {"title": "Data Analyst", "company": "OYO Rooms", "years": 1},
        ],
        "education": [
            {"degree": "M.Sc Data Science", "institution": "IIT Madras", "year": "2021"},
        ],
        "certifications": ["Tableau Desktop Certified", "Power BI Data Analyst"],
        "projects": [
            {
                "name": "Business Intelligence Platform",
                "description": "Power BI and Tableau dashboard suite for C-level reporting with SQL data pipeline",
                "tech_stack": ["sql", "power bi", "tableau", "python"],
            },
            {
                "name": "Customer Churn Analysis",
                "description": "Predictive churn model using Python and R for statistical analysis",
                "tech_stack": ["python", "r", "sql", "excel"],
            },
        ],
        "summary": "Senior data analyst with expertise in BI dashboards and predictive analytics.",
    },
    {
        "name": "Kavitha Raman",
        "email": "kavitha.raman@example.com",
        "phone": "+91-9876543214",
        "job_role": "Data Analyst",
        "skills": ["sql", "excel", "data analysis", "python"],
        "experience_years": 1,
        "roles": [{"title": "Junior Analyst", "company": "Deloitte", "years": 1}],
        "education": [{"degree": "B.Com", "institution": "Madras University", "year": "2023"}],
        "certifications": [],
        "projects": [
            {
                "name": "Financial Report Automation",
                "description": "Excel VBA script for automated financial reporting",
                "tech_stack": ["excel", "sql"],
            }
        ],
        "summary": "Junior analyst with Excel and SQL skills, learning Python.",
    },
    {
        "name": "Amit Tiwari",
        "email": "amit.tiwari@example.com",
        "phone": "+91-9876543215",
        "job_role": "Data Analyst",
        "skills": ["tableau", "excel", "sql"],
        "experience_years": 4,
        "roles": [{"title": "BI Analyst", "company": "Cognizant", "years": 4}],
        "education": [{"degree": "MBA Business Analytics", "institution": "XLRI", "year": "2020"}],
        "certifications": ["Tableau Desktop Specialist"],
        "projects": [
            {
                "name": "Supply Chain Dashboard",
                "description": "Tableau supply chain monitoring dashboard",
                "tech_stack": ["tableau", "sql", "excel"],
            }
        ],
        "summary": "BI analyst with 4 years building Tableau dashboards for supply chain.",
    },
    {
        "name": "Nisha Bose",
        "email": "nisha.bose@example.com",
        "phone": "+91-9876543216",
        "job_role": "ML Engineer",
        "skills": ["python", "tensorflow", "pytorch"],
        "experience_years": 0,
        "roles": [],
        "education": [{"degree": "B.Tech CSE", "institution": "Jadavpur University", "year": "2024"}],
        "certifications": [],
        "projects": [
            {
                "name": "Digit Recognition",
                "description": "MNIST digit recognition using TensorFlow as final year project",
                "tech_stack": ["tensorflow", "python"],
            }
        ],
        "summary": "Fresh graduate with deep learning project experience.",
    },

    # ── Full Stack candidates (for Job 4 — Full Stack Developer) ──
    {
        "name": "Suresh Gowda",
        "email": "suresh.gowda@example.com",
        "phone": "+91-9876543217",
        "job_role": "Full Stack Developer",
        "skills": ["react", "nodejs", "python", "mongodb", "rest api", "docker", "aws", "typescript"],
        "experience_years": 4,
        "roles": [
            {"title": "Full Stack Developer", "company": "CRED", "years": 2},
            {"title": "Software Engineer", "company": "Freshworks", "years": 2},
        ],
        "education": [{"degree": "B.Tech Computer Science", "institution": "RV College of Engineering", "year": "2020"}],
        "certifications": ["AWS Developer Associate", "MongoDB Certified Developer"],
        "projects": [
            {
                "name": "FinTech Platform",
                "description": "Full stack fintech app with React frontend, Node.js API, and MongoDB",
                "tech_stack": ["react", "nodejs", "mongodb", "docker"],
            },
            {
                "name": "Microservices System",
                "description": "Python microservices deployed on AWS with REST API design",
                "tech_stack": ["python", "rest api", "aws", "docker"],
            },
        ],
        "summary": "Full stack developer with 4 years building React + Node.js + Python systems.",
    },
    {
        "name": "Deepa Rao",
        "email": "deepa.rao@example.com",
        "phone": "+91-9876543218",
        "job_role": "Full Stack Developer",
        "skills": ["react", "python", "rest api", "sql"],
        "experience_years": 2,
        "roles": [{"title": "Software Developer", "company": "Mindtree", "years": 2}],
        "education": [{"degree": "B.Tech IT", "institution": "SRM University", "year": "2022"}],
        "certifications": [],
        "projects": [
            {
                "name": "CRM Application",
                "description": "React frontend with Python Flask backend and SQL database",
                "tech_stack": ["react", "python", "sql", "rest api"],
            }
        ],
        "summary": "Full stack developer experienced with React and Python backends.",
    },
    {
        "name": "Gaurav Kumar",
        "email": "gaurav.kumar@example.com",
        "phone": "+91-9876543219",
        "job_role": "Full Stack Developer",
        "skills": ["vue", "nodejs", "mongodb", "express"],
        "experience_years": 3,
        "roles": [{"title": "MEAN Stack Developer", "company": "Syntel", "years": 3}],
        "education": [{"degree": "B.Sc CS", "institution": "Pune University", "year": "2021"}],
        "certifications": [],
        "projects": [
            {
                "name": "Task Manager App",
                "description": "MEAN stack task management app with Vue frontend",
                "tech_stack": ["vue", "nodejs", "mongodb", "express"],
            }
        ],
        "summary": "MEAN stack developer with Vue.js experience, adapting to React.",
    },
    {
        "name": "Lakshmi Reddy",
        "email": "lakshmi.reddy@example.com",
        "phone": "+91-9876543220",
        "job_role": "Full Stack Developer",
        "skills": ["html", "css", "javascript", "php"],
        "experience_years": 5,
        "roles": [{"title": "Web Developer", "company": "Freelance", "years": 5}],
        "education": [{"degree": "BCA", "institution": "Andhra University", "year": "2019"}],
        "certifications": [],
        "projects": [
            {
                "name": "E-Commerce Site",
                "description": "PHP-based e-commerce website with MySQL backend",
                "tech_stack": ["php", "html", "css", "javascript"],
            }
        ],
        "summary": "Experienced web developer with PHP and frontend skills.",
    },
]


class Command(BaseCommand):
    help = "Seed the database with realistic jobs, candidates, and ranking results."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear all existing seed data before inserting.",
        )

    def handle(self, *args, **options):
        from jobs.models import Job
        from resumes.models import Resume
        from candidates.models import CandidateProfile
        from ranking.models import RankingResult
        from ai_pipeline.ranker import compute_total_score, parse_jd, generate_justification

        if options["clear"]:
            self.stdout.write("Clearing existing data...")
            RankingResult.objects.all().delete()
            CandidateProfile.objects.all().delete()
            Resume.objects.all().delete()
            Job.objects.all().delete()
            self.stdout.write(self.style.WARNING("All data cleared."))

        # ── 1. Create Jobs ──
        self.stdout.write("Creating 5 jobs...")
        created_jobs = []
        for job_data in JOBS:
            job, created = Job.objects.get_or_create(
                title=job_data["title"],
                defaults={k: v for k, v in job_data.items() if k != "title"},
            )
            if created:
                self.stdout.write(f"  + Job: {job.title}")
            else:
                self.stdout.write(f"  ~ Job already exists: {job.title}")
            created_jobs.append(job)

        # ── 2. Create Resumes + CandidateProfiles ──
        self.stdout.write(f"\nCreating {len(CANDIDATES)} candidates...")
        created_profiles = []

        for i, cand in enumerate(CANDIDATES):
            # Build structured profile
            profile = {
                "contact": {
                    "name": cand["name"],
                    "email": cand["email"],
                    "phone": cand["phone"],
                    "linkedin": "",
                    "github": "",
                },
                "skills": cand["skills"],
                "skill_categories": _categorize_skills(cand["skills"]),
                "experience_years": {
                    "total_years": cand["experience_years"],
                    "roles": cand["roles"],
                    "timeline": [],
                },
                "projects": cand["projects"],
                "education": cand["education"],
                "certifications": cand["certifications"],
                "summary": cand["summary"],
                "extraction_method": "seed_data",
            }

            # Fake file content (minimal, not actually parsed)
            fake_pdf = b"%PDF-1.4 seed-data-placeholder"
            filename = f"{cand['name'].lower().replace(' ', '_')}.pdf"
            content_hash = hashlib.sha256(
                (cand["email"] + cand["name"]).encode()
            ).hexdigest()

            # Skip if already exists
            if Resume.objects.filter(content_hash=content_hash).exists():
                self.stdout.write(f"  ~ Candidate exists: {cand['name']}")
                try:
                    resume = Resume.objects.get(content_hash=content_hash)
                    created_profiles.append(resume.candidate_profile)
                except Exception:
                    pass
                continue

            # Create Resume
            resume = Resume(
                filename=filename,
                file_type=".pdf",
                job_role=cand["job_role"],
                status="done",
                content_hash=content_hash,
                parse_confidence=0.95,
                raw_text=cand["summary"],
                parsed_sections={
                    "experience": " ".join(r.get("title", "") for r in cand["roles"]),
                    "skills": " ".join(cand["skills"]),
                },
            )
            resume.file.save(filename, ContentFile(fake_pdf), save=True)

            # Create CandidateProfile
            cp = CandidateProfile.objects.create(
                resume=resume,
                structured_profile=profile,
                profile_text=_profile_to_text(profile),
                embedding_vector=[],
            )
            created_profiles.append(cp)
            self.stdout.write(f"  + Candidate: {cand['name']}")

        # ── 3. Compute and store RankingResults ──
        self.stdout.write("\nComputing rankings (no LLM — NLP fallback)...")
        os.environ.setdefault("GROQ_API_KEY", "")  # disable Groq for seed

        for job in created_jobs:
            ranked = 0
            jd_requirements = parse_jd(job.description)
            # Inject structured skills from the job model (more reliable than NLP parse)
            jd_requirements["required_skills"] = job.required_skills or jd_requirements.get("required_skills", [])
            jd_requirements["preferred_skills"] = job.preferred_skills or []
            jd_requirements["min_experience_years"] = job.min_experience_years

            results = []
            for cp in created_profiles:
                scoring = compute_total_score(
                    cp.structured_profile, jd_requirements, job.description
                )
                justification = generate_justification(
                    cp.structured_profile, scoring, jd_requirements
                )
                results.append((cp, scoring, justification))

            # Sort by total score for rank_position
            results.sort(key=lambda x: x[1]["total_score"], reverse=True)

            for rank_pos, (cp, scoring, justification) in enumerate(results, start=1):
                RankingResult.objects.update_or_create(
                    job=job,
                    candidate=cp,
                    defaults={
                        "total_score": scoring["total_score"],
                        "skill_score": scoring["skill_score"],
                        "experience_score": scoring["experience_score"],
                        "project_score": scoring["project_score"],
                        "education_score": scoring["education_score"],
                        "score_breakdown": scoring["breakdown"],
                        "justification": justification,
                        "rank_position": rank_pos,
                    },
                )
                ranked += 1

            self.stdout.write(f"  [OK] {job.title}: {ranked} candidates ranked")

        # ── 4. Summary ──
        self.stdout.write(self.style.SUCCESS(
            f"\nSeed complete: {Job.objects.count()} jobs, "
            f"{CandidateProfile.objects.count()} candidates, "
            f"{RankingResult.objects.count()} ranking results."
        ))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SKILL_DOMAINS = {
    "frontend": ["react", "angular", "vue", "typescript", "javascript", "css", "html",
                 "redux", "webpack", "vite", "jest", "graphql"],
    "backend": ["python", "django", "fastapi", "nodejs", "java", "spring boot",
                "rest api", "postgresql", "mysql", "redis", "celery", "express"],
    "database": ["sql", "postgresql", "mysql", "mongodb", "redis", "sqlite"],
    "devops": ["docker", "kubernetes", "aws", "terraform", "ansible", "ci/cd"],
    "machine learning": ["tensorflow", "pytorch", "scikit-learn", "numpy", "pandas",
                         "mlflow", "keras", "spark", "matplotlib"],
    "data": ["sql", "tableau", "power bi", "excel", "r", "data analysis"],
}


def _categorize_skills(skills: list) -> dict:
    categories = {}
    for domain, domain_skills in SKILL_DOMAINS.items():
        matched = [s for s in skills if s in domain_skills]
        if matched:
            categories[domain] = matched
    return categories


def _profile_to_text(profile: dict) -> str:
    parts = []
    contact = profile.get("contact", {})
    if isinstance(contact, dict):
        parts.append(contact.get("name", ""))
    parts.append(" ".join(profile.get("skills", [])))
    exp = profile.get("experience_years", {})
    if isinstance(exp, dict):
        for role in exp.get("roles", []):
            parts.append(f"{role.get('title', '')} at {role.get('company', '')}")
    for proj in profile.get("projects", []):
        if isinstance(proj, dict):
            parts.append(proj.get("description", ""))
    parts.append(profile.get("summary", ""))
    return " ".join(filter(None, parts))


import os
