"""Document packet boundary splitter and classification engine (DocJev & Heuristic)."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import logging
import re
import httpx

from src.core.config import settings
from src.parser.loader import LoadedDocument

logger = logging.getLogger(__name__)


@dataclass
class DocumentSegment:
    """Represents a classified segment of a multi-document packet."""
    category: str  # "resume", "cover_letter", "transcripts", "job_description", "other"
    start_page: int  # 1-indexed
    end_page: int
    text: str
    confidence: float = 0.90
    title: Optional[str] = None


@dataclass
class PacketSplitResult:
    """Consolidated outcome of packet splitting and classification."""
    is_packet: bool
    primary_category: str
    segments: List[DocumentSegment] = field(default_factory=list)
    primary_resume_text: str = ""
    engine: str = "heuristic_boundary"
    page_count: int = 1


class DocumentSplitter:
    """Intelligently detects boundaries in bundled application files and classifies document types."""

    DOCUMENT_CATEGORIES = ["resume", "cover_letter", "transcripts", "job_description", "portfolio", "other"]

    @classmethod
    def process(cls, doc: LoadedDocument) -> PacketSplitResult:
        """Process a loaded document, classify its components, and isolate the resume."""
        # 1. Single page document shortcut
        if doc.page_count <= 1 or not doc.pages or len(doc.pages) == 1:
            category = cls._classify_single_page(doc.raw_text)
            segment = DocumentSegment(
                category=category,
                start_page=1,
                end_page=1,
                text=doc.raw_text,
                confidence=0.95
            )
            return PacketSplitResult(
                is_packet=False,
                primary_category=category,
                segments=[segment],
                primary_resume_text=doc.raw_text if category == "resume" else doc.raw_text,
                engine="direct_single_page",
                page_count=1
            )

        # 2. Try TypeSafe / DocJev if API key is present
        if settings.can_use_docjev:
            try:
                jev_result = cls._split_with_typesafe(doc)
                if jev_result and jev_result.segments:
                    return jev_result
            except Exception as e:
                logger.warning(f"TypeSafe DocJev splitting failed: {e}. Falling back to heuristic boundary splitter.")

        # 3. Fallback to Local Heuristic Boundary Detection
        return cls._split_heuristically(doc)

    # --- TypeSafe / DocJev Decision Model Integration ---

    @classmethod
    def _split_with_typesafe(cls, doc: LoadedDocument) -> Optional[PacketSplitResult]:
        """Call TypeSafe Jev decision API to classify page ranges and segment boundaries."""
        headers = {
            "Authorization": f"Bearer {settings.typesafe_api_key}",
            "Content-Type": "application/json"
        }

        # Build payload summarizing each page (first 800 chars of each page for fast latency)
        pages_summary = [
            {"page": idx + 1, "preview": page_text[:800].strip()}
            for idx, page_text in enumerate(doc.pages)
        ]

        payload = {
            "task": "document_classification_and_splitting",
            "categories": cls.DOCUMENT_CATEGORIES,
            "rules": [
                "A resume contains candidate work history, education, and technical skills.",
                "A cover letter addresses a hiring manager with salutations (Dear, Sincerely) and pitch paragraphs.",
                "Transcripts contain course codes, semester grades, and university registrars.",
                "A job description lists candidate requirements, company perks, and responsibilities."
            ],
            "document": {
                "filename": doc.filename or "uploaded_document",
                "page_count": doc.page_count,
                "pages": pages_summary
            }
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(settings.typesafe_endpoint, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    segments = []
                    cuts = data.get("segments", [])
                    
                    for cut in cuts:
                        cat = cut.get("category", "other").lower()
                        s_page = cut.get("start_page", 1)
                        e_page = cut.get("end_page", s_page)
                        
                        # Stitch corresponding pages
                        seg_text = "\n\n".join(
                            doc.pages[p - 1] for p in range(s_page, min(e_page + 1, len(doc.pages) + 1))
                            if 0 <= p - 1 < len(doc.pages)
                        )
                        
                        segments.append(DocumentSegment(
                            category=cat,
                            start_page=s_page,
                            end_page=e_page,
                            text=seg_text,
                            confidence=cut.get("confidence", 0.95),
                            title=cut.get("title")
                        ))

                    if segments:
                        # Extract resume segments
                        resume_segments = [s for s in segments if s.category == "resume"]
                        primary_text = "\n\n".join(s.text for s in resume_segments) if resume_segments else doc.raw_text
                        primary_cat = resume_segments[0].category if resume_segments else segments[0].category

                        return PacketSplitResult(
                            is_packet=len(segments) > 1,
                            primary_category=primary_cat,
                            segments=segments,
                            primary_resume_text=primary_text,
                            engine="docjev_typesafe",
                            page_count=doc.page_count
                        )
        except Exception as e:
            logger.debug(f"Direct TypeSafe call failed: {e}")

        return None

    # --- Deterministic Local Boundary Detection ---

    @classmethod
    def _split_heuristically(cls, doc: LoadedDocument) -> PacketSplitResult:
        """Segment document by analyzing typographic headers, salutations, and page transitions."""
        page_categories = []
        for p_idx, page_text in enumerate(doc.pages):
            cat = cls._classify_single_page(page_text)
            page_categories.append(cat)

        # Merge contiguous pages of the same category
        segments: List[DocumentSegment] = []
        if not page_categories:
            return PacketSplitResult(
                is_packet=False,
                primary_category="resume",
                primary_resume_text=doc.raw_text,
                engine="heuristic_boundary",
                page_count=doc.page_count
            )

        curr_cat = page_categories[0]
        start_p = 1

        for i in range(1, len(page_categories)):
            cat = page_categories[i]
            # Transition to a new document boundary
            if cat != curr_cat:
                seg_text = "\n\n".join(doc.pages[start_p - 1:i])
                segments.append(DocumentSegment(
                    category=curr_cat,
                    start_page=start_p,
                    end_page=i,
                    text=seg_text,
                    confidence=0.88
                ))
                curr_cat = cat
                start_p = i + 1

        # Append final segment
        seg_text = "\n\n".join(doc.pages[start_p - 1:len(page_categories)])
        segments.append(DocumentSegment(
            category=curr_cat,
            start_page=start_p,
            end_page=len(page_categories),
            text=seg_text,
            confidence=0.88
        ))

        # Determine primary resume text
        resume_segments = [s for s in segments if s.category == "resume"]
        if resume_segments:
            primary_text = "\n\n".join(s.text for s in resume_segments)
            primary_cat = "resume"
        else:
            primary_text = doc.raw_text
            primary_cat = segments[0].category if segments else "resume"

        return PacketSplitResult(
            is_packet=len(segments) > 1,
            primary_category=primary_cat,
            segments=segments,
            primary_resume_text=primary_text,
            engine="heuristic_boundary",
            page_count=doc.page_count
        )

    # --- Single Page Heuristic Classifier ---

    @classmethod
    def _classify_single_page(cls, text: str) -> str:
        """Classify a single page based on keyword indicators and structural hallmarks."""
        if not text or not text.strip():
            return "other"

        clean = text.lower()

        # Cover Letter markers
        cover_letter_signals = [
            r"dear\s+(hiring\s+manager|recruiter|team|mr\.|ms\.|dr\.)",
            r"to\s+whom\s+it\s+may\s+concern",
            r"i\s+am\s+writing\s+to\s+express\s+(my\s+)?interest",
            r"sincerely,",
            r"best\s+regards,",
            r"warm\s+regards,",
            r"cover\s+letter"
        ]
        if any(re.search(pat, clean) for pat in cover_letter_signals):
            return "cover_letter"

        # Transcript markers
        transcript_signals = [
            r"official\s+transcript",
            r"academic\s+transcript",
            r"registrar\s+signature",
            r"grade\s+point\s+average",
            r"cumulative\s+gpa",
            r"course\s+credits",
            r"semester\s+credits"
        ]
        if any(re.search(pat, clean) for pat in transcript_signals):
            return "transcripts"

        # Job Description markers
        jd_signals = [
            r"we\s+are\s+looking\s+for",
            r"responsibilities\s+and\s+duties",
            r"what\s+you('ll|\s+will)\s+do",
            r"what\s+we\s+offer",
            r"benefits\s+and\s+perks",
            r"job\s+requirements:"
        ]
        if any(re.search(pat, clean) for pat in jd_signals):
            return "job_description"

        # Resume markers (work experience, skills, education)
        resume_signals = [
            r"work\s+experience",
            r"professional\s+experience",
            r"technical\s+skills",
            r"education",
            r"projects",
            r"certifications",
            r"career\s+summary",
            r"employment\s+history"
        ]
        resume_match_count = sum(1 for pat in resume_signals if re.search(pat, clean))
        if resume_match_count >= 2:
            return "resume"

        # Contact info check (resume indicator)
        has_email = bool(re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text))
        has_phone = bool(re.search(r"\+?\d[\d\s().-]{7,}\d", text))
        if has_email and (has_phone or resume_match_count >= 1):
            return "resume"

        return "resume" if resume_match_count >= 1 else "other"
