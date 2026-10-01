"""Resume parsing and ATS evaluation endpoints."""

import time
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from pydantic import BaseModel

from src.core.config import settings
from src.parser.loader import DocumentLoader
from src.parser.normalizer import TextNormalizer
from src.engine.extractor import CandidateExtractor
from src.engine.matcher import ATSMatcher
from src.api.schemas.candidate import CandidateProfile
from src.api.schemas.matching import ATSScoreReport, CandidateEvaluationResponse

router = APIRouter()


class ScoreRequest(BaseModel):
    profile: CandidateProfile
    job_description: str


def _validate_file(file: UploadFile) -> str:
    """Validate file presence, extension, and content size."""
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resume file is required."
        )

    suffix = Path(file.filename).suffix.lower()
    if suffix not in settings.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file extension '{suffix}'. Supported: {', '.join(settings.allowed_extensions)}"
        )
    return suffix


@router.post("/parse", response_model=CandidateProfile, tags=["parser"])
async def parse_resume(
    file: UploadFile = File(...),
    force_heuristic: bool = Form(False)
):
    """Upload a resume file (PDF, DOCX, TXT) and return structured candidate profile."""
    _validate_file(file)

    try:
        content = await file.read()
        if len(content) > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {settings.max_file_size_bytes / (1024*1024):.0f}MB."
            )

        doc = DocumentLoader.load_bytes(content, filename=file.filename)
        normalized = TextNormalizer.normalize(doc.raw_text)
        extractor = CandidateExtractor(force_heuristic=force_heuristic)
        profile = extractor.extract(normalized)
        return profile
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error parsing resume: {str(e)}"
        )


@router.post("/score", response_model=ATSScoreReport, tags=["matching"])
async def score_candidate(payload: ScoreRequest):
    """Evaluate an existing candidate profile against a job description."""
    try:
        matcher = ATSMatcher()
        report = matcher.evaluate(payload.profile, payload.job_description)
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error scoring candidate: {str(e)}"
        )


@router.post("/analyze", response_model=CandidateEvaluationResponse, tags=["pipeline"])
async def analyze_resume_and_match(
    file: UploadFile = File(...),
    job_description: Optional[str] = Form(None),
    force_heuristic: bool = Form(False)
):
    """Single-call endpoint: parse resume file and evaluate against target job description."""
    _validate_file(file)
    start_time = time.time()

    try:
        content = await file.read()
        if len(content) > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {settings.max_file_size_bytes / (1024*1024):.0f}MB."
            )

        doc = DocumentLoader.load_bytes(content, filename=file.filename)
        normalized = TextNormalizer.normalize(doc.raw_text)
        extractor = CandidateExtractor(force_heuristic=force_heuristic)
        profile = extractor.extract(normalized)

        matcher = ATSMatcher()
        score_report = matcher.evaluate(profile, job_description or "")

        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        return CandidateEvaluationResponse(
            profile=profile,
            score_report=score_report,
            processing_time_ms=elapsed_ms,
            engine_mode=profile.extraction_mode
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Pipeline evaluation error: {str(e)}"
        )
