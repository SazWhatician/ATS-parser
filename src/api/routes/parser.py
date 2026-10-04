"""Resume parsing, packet splitting, and ATS evaluation endpoints."""

import time
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from pydantic import BaseModel

from src.core.config import settings
from src.parser.loader import DocumentLoader
from src.parser.splitter import DocumentSplitter, PacketSplitResult
from src.parser.normalizer import TextNormalizer
from src.engine.extractor import CandidateExtractor
from src.engine.matcher import ATSMatcher
from src.api.schemas.candidate import CandidateProfile
from src.api.schemas.matching import ATSScoreReport, CandidateEvaluationResponse

router = APIRouter()


class ScoreRequest(BaseModel):
    profile: CandidateProfile
    job_description: str


class SegmentResponse(BaseModel):
    category: str
    start_page: int
    end_page: int
    confidence: float
    text_preview: str


class PacketSplitResponse(BaseModel):
    filename: str
    page_count: int
    is_packet: bool
    primary_category: str
    engine: str
    segments: List[SegmentResponse]


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


@router.post("/split", response_model=PacketSplitResponse, tags=["packet"])
async def split_packet(file: UploadFile = File(...)):
    """Upload a document packet to detect boundaries and classify sub-documents (DocJev & Heuristic)."""
    _validate_file(file)
    try:
        content = await file.read()
        if len(content) > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {settings.max_file_size_bytes / (1024*1024):.0f}MB."
            )

        doc = DocumentLoader.load_bytes(content, filename=file.filename)
        split_result = DocumentSplitter.process(doc)

        segment_responses = [
            SegmentResponse(
                category=s.category,
                start_page=s.start_page,
                end_page=s.end_page,
                confidence=s.confidence,
                text_preview=s.text[:200] + ("..." if len(s.text) > 200 else "")
            )
            for s in split_result.segments
        ]

        return PacketSplitResponse(
            filename=file.filename,
            page_count=doc.page_count,
            is_packet=split_result.is_packet,
            primary_category=split_result.primary_category,
            engine=split_result.engine,
            segments=segment_responses
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error analyzing document packet: {str(e)}"
        )


@router.post("/parse", response_model=CandidateProfile, tags=["parser"])
async def parse_resume(
    file: UploadFile = File(...),
    force_heuristic: bool = Form(False)
):
    """Upload a resume or application packet; automatically isolates resume, normalizes, and extracts candidate profile."""
    _validate_file(file)

    try:
        content = await file.read()
        if len(content) > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {settings.max_file_size_bytes / (1024*1024):.0f}MB."
            )

        # Layer 1: Spatial Ingestion
        doc = DocumentLoader.load_bytes(content, filename=file.filename)

        # Layer 2: Packet Boundary Splitting & Document Classification
        split_result = DocumentSplitter.process(doc)
        resume_text = split_result.primary_resume_text

        # Layer 3: Fuzzy & Typographic Section Normalization
        normalized = TextNormalizer.normalize(resume_text)

        # Layer 4: Neuro-Symbolic Hybrid Extraction
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
    """End-to-end 4-layer pipeline: spatial load -> packet split -> fuzzy normalize -> hybrid extract -> rubric match."""
    _validate_file(file)
    start_time = time.time()

    try:
        content = await file.read()
        if len(content) > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {settings.max_file_size_bytes / (1024*1024):.0f}MB."
            )

        # Layer 1: Spatial layout-aware ingestion
        doc = DocumentLoader.load_bytes(content, filename=file.filename)

        # Layer 2: Packet splitting & classification
        split_result = DocumentSplitter.process(doc)
        resume_text = split_result.primary_resume_text

        # Layer 3: Fuzzy section normalizer
        normalized = TextNormalizer.normalize(resume_text)

        # Layer 4: Hybrid extraction
        extractor = CandidateExtractor(force_heuristic=force_heuristic)
        profile = extractor.extract(normalized)

        # Rubric Matcher
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
