# ATS Resume Parser & Match Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a clean, bloat-free standalone ATS Resume Parser & Evaluation Engine with an embedded anti-AI slop testing workstation, offline heuristic resilience, and phase-wise study documentation crediting `saswa`.

**Architecture:** A lightweight FastAPI service with modular document ingestion (`src/parser/`), candidate extraction (`src/engine/`), rubric-based ATS matching (`src/engine/matcher.py`), clean API routes (`src/api/`), and an embedded single-page dark-mode workstation UI (`src/static/`) that runs 100% locally with zero external API calls by default.

**Tech Stack:** Python 3.10+, FastAPI, Pydantic v2, PyMuPDF (`fitz`), python-docx, pdfplumber, Uvicorn, Vanilla HTML5/CSS3/ES6.

**Spec:** `docs/superpowers/specs/2026-10-01-ats-resume-parser-design.md`

## Global Constraints
- Zero secret leakage: Never copy, commit, or log API keys. Clean `.env.example` with empty values.
- 100% local-first resilience: Default heuristic engine runs completely offline with zero external network hits.
- Never push to git remote: All work remains local.
- No dead code: Purge bill classification, stale backups, duplicate vector stores, scraper microservices, and unneeded daemons.
- Phase-wise study documentation: Create dedicated `study_docs/phase-1.md` through `study_docs/phase-4.md` containing both Layman Analogies and Technical Walkthroughs.
- Author credit: Credit `saswa` as author in all documentation and headers.

## Review Focus
- Corrupted or password-protected PDF upload: Expect clean 400/422 validation response, not unhandled 500 crash.
- Missing contact details in resume: Parser gracefully defaults fields to `None` or empty lists without throwing KeyError.
- Long text overflows in resume parsing: Text normalizer bounds chunk lengths cleanly.
- Empty or whitespace-only job description in scoring: Matcher handles gracefully, returning candidate profile with neutral score notification.
- Offline execution verification: Entire test suite and local workstation UI work without internet access or API credentials.

---

### Task 1: Project Setup, Configuration, Base Schemas & Master Study Docs

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `src/core/config.py`
- Create: `src/api/schemas/candidate.py`
- Create: `src/api/schemas/matching.py`
- Create: `study_docs/README.md`
- Test: `tests/test_config_and_schemas.py`

**Interfaces:**
- Consumes: Standard library & Pydantic v2 BaseSettings
- Produces: `settings` singleton from `src/core/config.py`, `CandidateProfile` from `src/api/schemas/candidate.py`, `ATSScoreReport` from `src/api/schemas/matching.py`

- [ ] **Step 1: Write failing tests for configuration and Pydantic schemas**

```python
# tests/test_config_and_schemas.py
import pytest
from src.core.config import Settings
from src.api.schemas.candidate import CandidateProfile, ContactInfo, ExperienceItem, EducationItem
from src.api.schemas.matching import ATSScoreReport, ScoreCategory

def test_settings_defaults():
    s = Settings()
    assert s.app_name == "ATS Resume Parser & Match Engine"
    assert s.port == 8000
    assert s.has_llm_key is False

def test_candidate_profile_schema():
    profile = CandidateProfile(
        contact=ContactInfo(name="Jane Doe", email="jane@example.com"),
        summary="Experienced Software Engineer",
        skills=["Python", "FastAPI", "Docker"],
        experience=[
            ExperienceItem(
                company="TechCorp",
                role="Senior Engineer",
                duration="3 years",
                technologies=["Python", "PostgreSQL"]
            )
        ],
        education=[
            EducationItem(institution="MIT", degree="B.S. in Computer Science")
        ]
    )
    assert profile.contact.name == "Jane Doe"
    assert len(profile.skills) == 3

def test_ats_score_report_schema():
    report = ATSScoreReport(
        overall_score=85.5,
        match_level="Strong Match",
        categories={
            "technical_skills": ScoreCategory(score=90.0, weight=0.4, reasoning="Matches core skills"),
            "experience": ScoreCategory(score=80.0, weight=0.35, reasoning="Sufficient years")
        },
        strengths=["Strong Python background"],
        gaps=["No Kubernetes experience listed"]
    )
    assert report.overall_score == 85.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config_and_schemas.py -v`  
Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Implement project configuration, dependencies, schemas, and study docs master index**

1. Create `pyproject.toml` and `requirements.txt`:
```toml
# pyproject.toml
[project]
name = "ats-parser"
version = "0.1.0"
description = "Clean, local-first ATS Resume Parser & Evaluation Engine"
authors = [{ name = "saswa" }]
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn>=0.28.0",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.2.0",
    "python-multipart>=0.0.9",
    "pymupdf>=1.24.0",
    "pdfplumber>=0.11.0",
    "python-docx>=1.1.0",
    "httpx>=0.27.0"
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

2. Create `src/core/config.py`:
```python
# src/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ATS Resume Parser & Match Engine"
    app_version: str = "1.0.0"
    author: str = "saswa"
    port: int = 8000
    host: str = "0.0.0.0"
    debug: bool = False
    
    # LLM keys (optional - offline heuristic mode runs if blank)
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "google/gemini-2.0-flash-001"
    google_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    
    # Parser limits
    max_file_size_bytes: int = 15 * 1024 * 1024  # 15 MB
    temp_dir: str = "data/temp"

    @property
    def has_llm_key(self) -> bool:
        return bool(self.openrouter_api_key or self.google_api_key or self.openai_api_key)

settings = Settings()
```

3. Create `src/api/schemas/candidate.py` and `src/api/schemas/matching.py`.
4. Create `.env.example` with blank values.
5. Create `study_docs/README.md` outlining the 4-phase system architecture and file guide.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config_and_schemas.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add pyproject.toml requirements.txt .gitignore .env.example src/ study_docs/README.md tests/
git commit -m "chore: setup project foundation, schemas, and master study documentation"
```

---

### Task 2: Phase 1 — Document Loader & Text Normalizer Engine

**Files:**
- Create: `src/parser/loader.py`
- Create: `src/parser/normalizer.py`
- Create: `study_docs/phase-1.md`
- Test: `tests/test_loader.py`

**Interfaces:**
- Consumes: Raw file bytes / path (`Path`, `bytes`, `str`)
- Produces: `LoadedDocument(raw_text: str, file_type: str, page_count: int, metadata: dict)` and `NormalizedDocument(clean_text: str, sections: dict[str, str], word_count: int)`

- [ ] **Step 1: Write failing tests for document loading and normalization**

```python
# tests/test_loader.py
import pytest
from pathlib import Path
from src.parser.loader import DocumentLoader
from src.parser.normalizer import TextNormalizer

def test_plain_text_loading(tmp_path):
    sample_txt = tmp_path / "resume.txt"
    sample_txt.write_text("John Doe\nSoftware Engineer\nSkills: Python, FastAPI\nExperience:\nAcme Corp - 2 years", encoding="utf-8")
    
    doc = DocumentLoader.load_file(sample_txt)
    assert "John Doe" in doc.raw_text
    assert doc.file_type == "txt"

def test_text_normalization():
    dirty_text = "  John Doe  \r\n\r\n\tSenior Dev \xa0\xa0\n\nEXPERIENCE:\nWorked on backend.\n\nSKILLS:\nPython, SQL  "
    normalized = TextNormalizer.normalize(dirty_text)
    assert "John Doe" in normalized.clean_text
    assert "experience" in normalized.sections
    assert "skills" in normalized.sections
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_loader.py -v`  
Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Implement `loader.py`, `normalizer.py`, and `study_docs/phase-1.md`**

1. In `src/parser/loader.py`: Support PyMuPDF (`fitz`) with fallback to `pdfplumber`/`pypdf` for `.pdf`, `python-docx` for `.docx`, and encoding-tolerant reader for `.txt`.
2. In `src/parser/normalizer.py`: Clean non-printable artifacts, standardize line breaks and bullets, and implement section regex segmentation (`summary`, `experience`, `education`, `skills`, `projects`, `certifications`).
3. Write `study_docs/phase-1.md` detailing Phase 1:
   - **Layman Analogy**: The Digital Receptionist & Translator (taking messy paper/digital resumes, removing wrinkles, and categorizing into labeled folders).
   - **Technical Deep Dive**: Multi-engine PDF decoding, UTF-8 normalization, section detection state machine.
   - **File Index**: What `src/parser/loader.py` and `src/parser/normalizer.py` do line by line.
   - **Verification Instructions**: How to run the phase test.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_loader.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add src/parser/ tests/test_loader.py study_docs/phase-1.md
git commit -m "feat(parser): implement document loader, text normalizer, and phase-1 study doc"
```

---

### Task 3: Phase 2 — Candidate Entity Extraction Engine (Heuristic + LLM)

**Files:**
- Create: `src/core/llm.py`
- Create: `src/engine/heuristics.py`
- Create: `src/engine/extractor.py`
- Create: `study_docs/phase-2.md`
- Test: `tests/test_extractor.py`

**Interfaces:**
- Consumes: `NormalizedDocument` from Phase 1
- Produces: `CandidateProfile` Pydantic model

- [ ] **Step 1: Write failing tests for candidate profile extraction**

```python
# tests/test_extractor.py
import pytest
from src.parser.normalizer import TextNormalizer
from src.engine.extractor import CandidateExtractor

SAMPLE_RESUME = """
Jane Developer
Email: jane.dev@example.com | Phone: +1-555-0199 | Location: San Francisco, CA
LinkedIn: linkedin.com/in/janedev | GitHub: github.com/janedev

SUMMARY
Seasoned backend engineer with 5 years of experience in distributed systems.

TECHNICAL SKILLS
Languages: Python, Go, TypeScript, SQL
Frameworks: FastAPI, Django, React
Infrastructure: Docker, AWS, PostgreSQL, Redis

WORK EXPERIENCE
Senior Backend Engineer | Acme Innovations | 2021 - Present
- Architected high-throughput microservices using FastAPI and Redis.
- Reduced database query latency by 40% using PostgreSQL indexing.

Software Engineer | Beta Corp | 2019 - 2021
- Developed REST APIs and background worker pipelines in Python.

EDUCATION
B.S. in Computer Science | University of California, Berkeley | 2015 - 2019
"""

def test_heuristic_offline_extraction():
    norm_doc = TextNormalizer.normalize(SAMPLE_RESUME)
    extractor = CandidateExtractor(force_heuristic=True)
    profile = extractor.extract(norm_doc)

    assert profile.contact.name == "Jane Developer"
    assert profile.contact.email == "jane.dev@example.com"
    assert "github.com/janedev" in (profile.contact.github or "")
    assert "Python" in profile.skills
    assert "FastAPI" in profile.skills
    assert len(profile.experience) >= 2
    assert any("Acme" in exp.company for exp in profile.experience)
    assert profile.education[0].institution != ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_extractor.py -v`  
Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Implement `heuristics.py`, `llm.py`, `extractor.py`, and `study_docs/phase-2.md`**

1. `src/engine/heuristics.py`: Deterministic entity extraction using regex patterns for emails, phone numbers, social links, date range calculator, curated technical skills dictionary (covering 200+ technologies across languages, frameworks, cloud, databases), and section pattern matchers.
2. `src/core/llm.py`: Clean multi-provider client (OpenRouter, Gemini, OpenAI) with zero-cost fallback when no key is set.
3. `src/engine/extractor.py`: Coordinates extraction. Defaults to `heuristics.py` if no key is configured or when offline mode is selected; calls `llm.py` structured output when key is present.
4. Write `study_docs/phase-2.md`:
   - **Layman Analogy**: The Expert HR Sifter (reading through unformatted text, using a mental highlighter to pick out candidate identity, contact info, job history, and tech stack).
   - **Technical Deep Dive**: Regex token patterns, dictionary taxonomy lookup, date duration arithmetic, Pydantic schema validation.
   - **File Index**: Detailed breakdown of `src/engine/heuristics.py`, `src/core/llm.py`, and `src/engine/extractor.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_extractor.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add src/core/llm.py src/engine/ tests/test_extractor.py study_docs/phase-2.md
git commit -m "feat(engine): implement heuristic extraction, LLM adapter, and phase-2 study doc"
```

---

### Task 4: Phase 3 — Rubric-Based ATS Matcher & Gap Analysis

**Files:**
- Create: `src/engine/matcher.py`
- Create: `study_docs/phase-3.md`
- Test: `tests/test_matcher.py`

**Interfaces:**
- Consumes: `CandidateProfile` (from Phase 2) and `job_description: str`
- Produces: `ATSScoreReport` (overall score, category breakdown, key strengths, critical gaps, recommendation)

- [ ] **Step 1: Write failing tests for ATS job description matching**

```python
# tests/test_matcher.py
import pytest
from src.parser.normalizer import TextNormalizer
from src.engine.extractor import CandidateExtractor
from src.engine.matcher import ATSMatcher

SAMPLE_JD = """
Job Title: Senior Python Backend Engineer
Requirements:
- 4+ years of professional backend software engineering experience.
- Expert knowledge of Python, FastAPI, and PostgreSQL.
- Experience with Docker, Redis, and cloud infrastructure (AWS or GCP).
- Degree in Computer Science or equivalent practical experience.
Nice to have:
- Experience with Kubernetes and Kafka.
"""

def test_ats_matcher_scoring():
    # Use profile from extractor
    from tests.test_extractor import SAMPLE_RESUME
    norm_doc = TextNormalizer.normalize(SAMPLE_RESUME)
    profile = CandidateExtractor(force_heuristic=True).extract(norm_doc)

    matcher = ATSMatcher()
    report = matcher.evaluate(profile, SAMPLE_JD)

    assert report.overall_score >= 70.0
    assert "technical_skills" in report.categories
    assert "experience" in report.categories
    assert len(report.strengths) > 0
    assert any("Kubernetes" in gap or "Kafka" in gap for gap in report.gaps)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_matcher.py -v`  
Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Implement `matcher.py` and `study_docs/phase-3.md`**

1. `src/engine/matcher.py`:
   - Keyword & entity extraction from Job Description.
   - 4-Tier Rubric:
     - Technical Skills (40%): Required vs Optional skill overlaps.
     - Experience & Role Relevance (35%): Years of experience matched against requirements.
     - Education (15%): Degree level comparison.
     - Quality & Completeness (10%): Bullet clarity, contact completeness.
   - Gap Analysis: Computes missing skills and experience differentials.
   - Strengths Synthesis: Identifies exact high-matching criteria.
2. Write `study_docs/phase-3.md`:
   - **Layman Analogy**: The Impartial Judge & Rubric Scorer (comparing candidate capabilities against job wishlist, calculating percentage fit, highlighting exact reasons for hire/pause).
   - **Technical Deep Dive**: Weighted scoring mathematics, set intersection & token similarity algorithms, gap generation logic.
   - **File Index**: Code walkthrough of `src/engine/matcher.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_matcher.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add src/engine/matcher.py tests/test_matcher.py study_docs/phase-3.md
git commit -m "feat(engine): implement ATS rubric matcher, gap analysis, and phase-3 study doc"
```

---

### Task 5: Phase 4 — REST API Endpoints & Anti-AI Slop Workstation UI

**Files:**
- Create: `src/api/routes/health.py`
- Create: `src/api/routes/parser.py`
- Create: `src/api/router.py`
- Create: `src/static/index.html`
- Create: `src/static/styles.css`
- Create: `src/static/app.js`
- Create: `src/main.py`
- Create: `study_docs/phase-4.md`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: Multipart upload & JSON request bodies
- Produces: REST endpoints (`/health`, `/parse`, `/score`, `/analyze`) and browser workstation served at `/`

- [ ] **Step 1: Write failing tests for API routes**

```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "engine_mode" in data

def test_parse_endpoint():
    files = {"file": ("test_resume.txt", b"Jane Doe\nEmail: jane@test.com\nSkills: Python, Go", "text/plain")}
    response = client.post("/api/v1/parse", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["contact"]["name"] == "Jane Doe"
    assert "Python" in data["skills"]

def test_analyze_endpoint():
    files = {"file": ("test_resume.txt", b"Jane Doe\nEmail: jane@test.com\nSkills: Python, FastAPI\nExperience:\n5 years", "text/plain")}
    data = {"job_description": "Looking for a Python and FastAPI backend engineer with 4+ years experience."}
    response = client.post("/api/v1/analyze", files=files, data=data)
    assert response.status_code == 200
    result = response.json()
    assert "profile" in result
    assert "score_report" in result
    assert result["score_report"]["overall_score"] > 50
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py -v`  
Expected: FAIL with ModuleNotFoundError.

- [ ] **Step 3: Implement API endpoints, Workstation UI, and `study_docs/phase-4.md`**

1. Create `src/api/routes/health.py`, `parser.py`, and `router.py`.
2. Create `src/main.py`: Configures FastAPI, CORS, static file mounts for `/static` and root redirect, process timing middleware.
3. Build the Workstation UI in `src/static/`:
   - `index.html`: Executive dual-panel dashboard. Left: drag-and-drop file upload, JD presets, mode selector, action button. Right: candidate card, ATS score gauge, strengths & gaps, tabbed views for profile timeline, rubric scores, and raw JSON.
   - `styles.css`: Anti-AI slop theme (dark slate `#0f172a`, crisp `#1e293b` borders, emerald/amber accent status colors, JetBrains Mono/Inter typography, responsive grid).
   - `app.js`: Modern vanilla JS with async `fetch`, drag-and-drop file handler, preset loader, clipboard copy, dynamic tab switching.
4. Write `study_docs/phase-4.md`:
   - **Layman Analogy**: The Airport Control Tower & Interactive Dashboard (handling incoming cargo safely, routing it to workers, and projecting clean flight data onto big screens).
   - **Technical Deep Dive**: FastAPI routing, multipart stream parsing, HTTP response serialization, static file serving, UI state management.
   - **File Index**: Code walkthrough of `src/main.py`, `src/api/routes/parser.py`, and `src/static/*`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_api.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add src/ tests/test_api.py study_docs/phase-4.md
git commit -m "feat(api): implement REST routes, workstation UI, and phase-4 study doc"
```

---

### Task 6: Project Finalization & Comprehensive README Crediting saswa

**Files:**
- Create: `README.md`
- Modify: `study_docs/README.md`
- Verify: Full test suite and local server launch

- [ ] **Step 1: Write comprehensive `README.md`**
- Professional project documentation crediting `saswa` as the author and developer.
- Clear Quickstart (`uvicorn src.main:app --reload` or `python src/main.py`).
- Feature walkthrough (Universal document parser, Offline Heuristic Engine, LLM Enhanced Engine, ATS Match Rubric, Interactive Workstation).
- Architecture diagram and link to `study_docs/`.
- API Reference with sample curl commands and request/response payloads.

- [ ] **Step 2: Update `study_docs/README.md` to reflect complete green status across all 4 phases**

- [ ] **Step 3: Run complete test suite**

Run: `pytest -v`  
Expected: 100% PASS with 0 warnings or failures.

- [ ] **Step 4: Commit changes**

```bash
git add README.md study_docs/README.md
git commit -m "docs: finalize master README crediting saswa and sync study documentation"
```
