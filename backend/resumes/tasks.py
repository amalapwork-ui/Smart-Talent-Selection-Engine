import logging
from concurrent.futures import ThreadPoolExecutor, wait as _wait, ALL_COMPLETED
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def parse_resume_task(self, resume_id: int):
    """
    Parse resume file → extract profile → generate embedding.

    Speed optimisations applied here:
    - Groq LLM extraction and embedding-model warm-up run in parallel so the
      model load time is hidden behind the Groq network round-trip.
    - Embedding is generated once on the final merged profile.
    """
    from resumes.models import Resume
    from candidates.models import CandidateProfile
    from ai_pipeline.parser import parse_resume
    from ai_pipeline.extractor import (
        build_profile_regex, enrich_with_nltk,
        extract_with_groq, _merge_profiles,
    )
    from ai_pipeline.embeddings import (
        generate_embedding, get_embedding_model, profile_to_text, get_faiss_store,
    )

    try:
        resume = Resume.objects.get(id=resume_id)
    except Resume.DoesNotExist:
        logger.error("Resume %s not found.", resume_id)
        return

    resume.status = "processing"
    resume.save(update_fields=["status"])

    try:
        # ── Step 1: file → raw text ───────────────────────────────────────
        parse_result = parse_resume(resume.file.path)
        if parse_result.get("error") and not parse_result.get("text"):
            raise ValueError(f"Parsing failed: {parse_result['error']}")

        raw_text   = parse_result.get("text", "")
        sections   = parse_result.get("sections", {})
        confidence = parse_result.get("confidence", 0.0)
        resume.raw_text       = raw_text
        resume.parsed_sections = sections
        resume.parse_confidence = confidence
        resume.file_type = parse_result.get("file_type", resume.file_type)

        # ── Step 2: Layer 1 + 2 (fast, pure-Python) ──────────────────────
        profile = build_profile_regex(raw_text, sections)
        profile = enrich_with_nltk(profile, raw_text)

        # ── Step 3: Groq extraction + embedding model warm-up in parallel ─
        # Groq call is network I/O (~1-3s). Model load is CPU (~2-5s first
        # time, instant after). Running both concurrently hides whichever is
        # shorter behind the longer one.
        with ThreadPoolExecutor(max_workers=2) as pool:
            groq_future  = pool.submit(extract_with_groq, raw_text)
            model_future = pool.submit(get_embedding_model)   # warm-up / no-op
            _wait([groq_future, model_future], return_when=ALL_COMPLETED)

        llm_profile = groq_future.result()
        if llm_profile:
            profile = _merge_profiles(profile, llm_profile)
            profile["extraction_method"] = "regex+nltk+groq_merged"

        # ── Step 4: Generate embedding (model already warm) ───────────────
        profile_text = profile_to_text(profile)
        embedding    = generate_embedding(profile_text)
        profile["_embedding_text"] = profile_text

        # ── Step 5: Persist ───────────────────────────────────────────────
        candidate_profile, _ = CandidateProfile.objects.update_or_create(
            resume=resume,
            defaults={
                "structured_profile": profile,
                "embedding_vector":   embedding,
                "profile_text":       profile_text,
            },
        )

        # ── Step 6: FAISS index ───────────────────────────────────────────
        try:
            get_faiss_store().add_candidate(candidate_profile.id, embedding)
        except Exception as faiss_err:
            logger.warning("FAISS indexing failed for candidate %s: %s",
                           candidate_profile.id, faiss_err)

        resume.status = "done"
        resume.save(update_fields=[
            "status", "raw_text", "parsed_sections", "parse_confidence", "file_type",
        ])
        logger.info("Resume %s processed → profile %s", resume_id, candidate_profile.id)
        return {"resume_id": resume_id, "candidate_profile_id": candidate_profile.id}

    except Exception as exc:
        logger.exception("Error processing resume %s: %s", resume_id, exc)
        resume.status = "error"
        resume.error_message = str(exc)[:500]
        resume.save(update_fields=["status", "error_message"])
        raise self.retry(exc=exc)
