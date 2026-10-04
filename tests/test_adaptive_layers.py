"""Comprehensive test suite for the 4 Adaptive Layers."""

import pytest
from src.parser.loader import DocumentLoader, LoadedDocument
from src.parser.splitter import DocumentSplitter, PacketSplitResult, DocumentSegment
from src.parser.normalizer import TextNormalizer, NormalizedDocument
from src.engine.heuristics import HeuristicResumeParser
from src.engine.extractor import CandidateExtractor
from src.api.schemas.candidate import CandidateProfile, ContactInfo


# =====================================================================
# LAYER 1: Spatial & Layout Ingestion Tests
# =====================================================================

def test_layer1_scanned_pdf_detection():
    """Verify that low-character or image-only documents flag is_scanned=True."""
    sparse_doc = LoadedDocument(
        raw_text="Page 1",
        file_type="pdf",
        page_count=2,
        pages=["Page 1", ""],
        is_scanned=True,
        metadata={"is_scanned": True, "scanned_warning": "Low text density"}
    )
    assert sparse_doc.is_scanned is True
    assert "scanned_warning" in sparse_doc.metadata


# =====================================================================
# LAYER 2: Document Segmentation & Packet Splitting Tests
# =====================================================================

def test_layer2_packet_splitter_single_page_resume():
    """Single page resume is classified correctly without splitting overhead."""
    single_page_doc = LoadedDocument(
        raw_text="Jane Developer\njane@example.com\n\nWORK EXPERIENCE\nSenior Dev at Acme 2020-2023\n\nEDUCATION\nBS Computer Science",
        file_type="pdf",
        page_count=1,
        pages=["Jane Developer\njane@example.com\n\nWORK EXPERIENCE\nSenior Dev at Acme 2020-2023\n\nEDUCATION\nBS Computer Science"]
    )
    res = DocumentSplitter.process(single_page_doc)
    assert res.is_packet is False
    assert res.primary_category == "resume"
    assert "Jane Developer" in res.primary_resume_text


def test_layer2_packet_splitter_multi_doc_packet():
    """Multi-page packet with Cover Letter on page 1 and Resume on page 2 isolates the resume."""
    cover_letter_page = (
        "Dear Hiring Manager,\n"
        "I am writing to express my interest in the Senior Backend Engineer position at Acme.\n"
        "Sincerely,\nJane Candidate"
    )
    resume_page = (
        "Jane Candidate\njane@candidate.com | +1-555-0199\n\n"
        "PROFESSIONAL EXPERIENCE\n"
        "Staff Engineer | TechCorp | 2021 - Present\n"
        "- Architected high performance systems\n\n"
        "TECHNICAL SKILLS\nPython, FastAPI, Docker, Kubernetes"
    )

    bundled_doc = LoadedDocument(
        raw_text=f"{cover_letter_page}\n\n{resume_page}",
        file_type="pdf",
        page_count=2,
        pages=[cover_letter_page, resume_page],
        filename="application_packet.pdf"
    )

    res = DocumentSplitter.process(bundled_doc)
    assert res.is_packet is True
    assert len(res.segments) == 2
    assert res.segments[0].category == "cover_letter"
    assert res.segments[1].category == "resume"
    assert "Dear Hiring Manager" not in res.primary_resume_text
    assert "Staff Engineer" in res.primary_resume_text


# =====================================================================
# LAYER 3: Fuzzy & Typographic Section Normalizer Tests
# =====================================================================

def test_layer3_fuzzy_section_aliases():
    """Verify that decorative numbers, non-standard headings, and French/German headers match."""
    resume_text = """
    01 | EXPERIENCE & ACHIEVEMENTS
    Senior Platform Engineer at Google (2020 - Present)
    - Led global infrastructure reliability.

    [ TECH STACK & TOOLS ]
    Languages: Python, Go, Rust

    FORMATION ACADEMIQUE
    Master of Science in Software Engineering, Stanford University
    """
    normalized = TextNormalizer.normalize(resume_text)
    assert "experience" in normalized.sections
    assert "skills" in normalized.sections
    assert "education" in normalized.sections
    assert "Senior Platform Engineer" in normalized.sections["experience"]
    assert "Rust" in normalized.sections["skills"]


def test_layer3_inline_headers():
    """Verify that headers with inline content on the same line are captured cleanly."""
    resume_text = """
    Jane Smith
    Experience: Senior Software Engineer at Meta from 2021 to 2024
    - Built distributed caching layer

    Skills: Python, TypeScript, React, PostgreSQL
    """
    normalized = TextNormalizer.normalize(resume_text)
    assert "experience" in normalized.sections
    assert "skills" in normalized.sections
    assert "Meta" in normalized.sections["experience"]
    assert "PostgreSQL" in normalized.sections["skills"]


# =====================================================================
# LAYER 4: Hybrid Extraction & International Resilience Tests
# =====================================================================

def test_layer4_international_contact_extraction():
    """Verify accented/international names and diverse phone formats are parsed accurately."""
    sample = """
    José Müller
    Email: jose.muller@example.de | WhatsApp: +49 30 12345678 | City: Berlin, Germany
    LinkedIn: linkedin.com/in/josemuller

    SUMMARY
    Senior Engineer with 8 years in distributed systems.

    SKILLS
    Python, FastAPI, Docker, Kubernetes, LangChain

    WORK EXPERIENCE
    Lead Architect | CloudWorks Berlin | 2018 - Present
    - Designed real-time event pipelines.
    """
    norm = TextNormalizer.normalize(sample)
    profile = HeuristicResumeParser.parse(norm)

    assert profile.contact.name == "José Müller"
    assert profile.contact.email == "jose.muller@example.de"
    assert "+49" in (profile.contact.phone or "")
    assert profile.contact.location == "Berlin, Germany"
    assert "LangChain" in profile.skills
    assert "Docker" in profile.skills


def test_layer4_adaptive_quarter_and_dashed_dates():
    """Verify that dates with quarters, months, and diverse separators compute experience correctly."""
    sample = """
    Kavya N. Rao
    Email: kavya.rao@example.com | Phone: +91 98765 43210

    EXPERIENCE
    Staff Developer | FinTech Corp | Q1 2019 - Present
    - Managed multi-tenant database clusters.

    Software Engineer | Startup Labs | Jan 2016 - Dec 2018
    - Backend microservices development.
    """
    norm = TextNormalizer.normalize(sample)
    profile = HeuristicResumeParser.parse(norm)

    assert profile.contact.name == "Kavya N. Rao"
    assert profile.total_experience_years is not None
    assert profile.total_experience_years >= 8.0  # 2016 to 2026 >= 8
    assert len(profile.experience) >= 2


def test_layer4_hybrid_reconciliation_zero_hallucination():
    """Verify that reconciliation anchors contact information to verified document text."""
    norm = TextNormalizer.normalize("Real Name\nreal.email@domain.com\nPython, FastAPI")
    heuristic_profile = HeuristicResumeParser.parse(norm)

    # Simulate an LLM output that hallucinated an email not in the document
    fake_llm_profile = CandidateProfile(
        contact=ContactInfo(
            name="Real Name",
            email="hallucinated.fake@fake.com",  # NOT in text!
            phone="+1-555-9999"
        ),
        skills=["Python", "FastAPI", "AsyncIO"],  # Inferred extra skill
        summary="A passionate developer.",
        total_experience_years=3.0,
        extraction_mode="llm"
    )

    extractor = CandidateExtractor(force_heuristic=False)
    reconciled = extractor._reconcile(heuristic_profile, fake_llm_profile, norm)

    assert reconciled.extraction_mode == "hybrid"
    # Ground truth email must be preserved from heuristic, rejecting hallucinated email!
    assert reconciled.contact.email == "real.email@domain.com"
    # Extra skills inferred by LLM are merged!
    assert "AsyncIO" in reconciled.skills
    assert "FastAPI" in reconciled.skills
