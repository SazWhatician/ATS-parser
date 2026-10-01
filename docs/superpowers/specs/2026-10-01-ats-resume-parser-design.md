# Architecture & Design Specification: Standalone ATS Resume Parser & Match Engine

**Date:** 2026-10-01  
**Author:** saswa  
**Status:** Approved  
**Target Repository:** `c:\Users\saswa\Desktop\parse ATS`  
**Reference Source:** `C:\Users\saswa\Desktop\HRMSXYZ\hiring2`  

---

## 1. Executive Summary & Goals

This project provides a standalone, production-grade **ATS Resume Parser and Match Engine** with an embedded, anti-AI slop testing workstation. It extracts the parsing, normalization, structured extraction, and rubric-based job-matching logic from a legacy hiring suite (`hiring2`) while eliminating redundant code, dead files, unneeded microservices, and external database locks.

### Core Objectives
1. **Zero Secret Leakage & Privacy**: Zero hardcoded API keys; clean `.env.example` with blank keys.
2. **Local-First & Offline Resilience**: A dual-engine setup where an offline heuristic/rule-based engine functions 100% locally with zero external network calls or API keys, seamlessly upgrading to LLM parsing when a key is provided.
3. **Dead Code Elimination (/ponytail)**: Purge legacy backups (`service_old_backup.py`, `providers_v1.py`), non-ATS features (bill classifier, invoice images), multi-vector store duplicate sprawl, scraper microservices, and background database sync loops.
4. **Anti-AI Slop Workstation UI**: A single-page, high-density, dark-mode technical workbench for testing resume uploads, previewing parsed candidate profiles, evaluating job fit, and inspecting structured JSON.
5. **Phase-Wise Study Documentation (`study_docs/`)**: Clear documentation providing both layman analogies and deep technical breakdowns for each phase of the project.
6. **No Remote Push**: Entirely local workspace; no remote git push.

---

## 2. System Architecture

```text
parse ATS/
├── study_docs/                    # Strictly Phase-Wise Learning Docs (Layman + Technical)
│   ├── README.md                  # Master Index & Architecture Map (Phase 1 through 4)
│   ├── phase-1.md                 # Phase 1: Core Document Ingestion & Normalizer
│   ├── phase-2.md                 # Phase 2: Entity Extraction Engine (Heuristic + LLM)
│   ├── phase-3.md                 # Phase 3: Rubric ATS Scoring & Gap Analysis Engine
│   └── phase-4.md                 # Phase 4: REST API & Interactive Workstation UI
├── src/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── parser.py          # /parse, /score, /analyze endpoints
│   │   │   └── health.py          # /health check
│   │   ├── schemas/
│   │   │   ├── candidate.py       # Pydantic schemas for candidate profile
│   │   │   └── matching.py        # Pydantic schemas for scoring & feedback
│   │   └── router.py              # Consolidated v1 router
│   ├── core/
│   │   ├── config.py              # Settings with Pydantic BaseSettings
│   │   └── llm.py                 # Multi-provider client (Gemini, OpenRouter, OpenAI, Local Mock)
│   ├── engine/
│   │   ├── extractor.py           # Structured extraction pipeline
│   │   ├── matcher.py             # Rubric-based ATS scoring engine
│   │   └── heuristics.py          # Regex & rule-based offline parser
│   ├── parser/
│   │   ├── loader.py              # Document loader (PDF via PyMuPDF/pdfplumber, DOCX, TXT)
│   │   └── normalizer.py          # Text sanitization, section detection, layout preservation
│   ├── static/
│   │   ├── index.html             # Sleek dark-mode workstation UI
│   │   ├── styles.css             # Anti-AI slop CSS styling
│   │   └── app.js                 # Workstation client logic & state management
│   ├── main.py                    # FastAPI entrypoint & static mount
│   └── __init__.py
├── .env.example                   # Clean template with placeholders
├── .gitignore                     # Git hygiene: ignores .env, __pycache__, uploads
├── pyproject.toml                 # UV / pip configuration
├── requirements.txt               # Pinned minimal dependencies
└── README.md                      # Complete project documentation crediting saswa
```

---

## 3. Component Specifications

### 3.1 Document Ingestion & Normalizer (`src/parser/`)
- **`loader.py`**:
  - Accepts raw files or byte streams.
  - Multi-engine PDF support: PyMuPDF (`fitz`) as primary for speed and accuracy; fallback to `pdfplumber` or `pypdf`.
  - Microsoft Word support: `python-docx` for `.docx` files.
  - Plaintext / Markdown support: Standard UTF-8 decoding with fallback encodings (`latin-1`, `cp1252`).
  - Graceful file validation: Size limits, MIME type verification, extension whitelisting (`.pdf`, `.docx`, `.txt`).
- **`normalizer.py`**:
  - Strips non-printable characters, cleans redundant line wraps, standardizes bullets and whitespace.
  - Identifies document headers and major resume sections (`Summary`, `Experience`, `Education`, `Skills`, `Projects`, `Certifications`).

### 3.2 Candidate Extraction Engine (`src/engine/`)
- **`heuristics.py`**:
  - Deterministic regex patterns for contact info (email, phone, LinkedIn, GitHub, portfolio).
  - Rule-based section parsing and token extraction.
  - Pre-trained dictionary matching for technical skills (programming languages, frameworks, cloud platforms, databases, developer tools).
  - Experience calculator: Computes year durations from detected date ranges (`YYYY - YYYY`, `Month YYYY - Present`).
- **`extractor.py`**:
  - Coordinates profile extraction.
  - Checks if an LLM is configured. If not, runs `heuristics.py`. If configured, passes normalized text to `llm.py` with structured Pydantic output validation.
- **`schemas/candidate.py`**:
  - `ContactInfo`: Full name, email, phone, location, links.
  - `ExperienceItem`: Company, role, duration, start/end dates, highlights, technologies used.
  - `EducationItem`: Institution, degree, field of study, graduation year.
  - `CandidateProfile`: Complete structured candidate representation.

### 3.3 ATS Scoring & Job Matcher (`src/engine/matcher.py`)
- Evaluates candidate profile against target job description:
  1. **Technical Skills Match (40% weight)**: Compares required/preferred skills in JD against candidate skill set.
  2. **Experience & Role Relevance (35% weight)**: Compares years of experience, seniority, and domain relevance.
  3. **Education & Credentials (15% weight)**: Matches minimum degree and certification requirements.
  4. **Document Quality & Clarity (10% weight)**: Readability, structure, and action-verb strength.
- Computes overall ATS score (0-100), individual sub-scores, and generates:
  - **Key Strengths**: Specific points where the candidate meets or exceeds requirements.
  - **Critical Gaps**: Missing keywords, required tech stack gaps, or experience deficiencies.
  - **Actionable Recommendation**: Clear hiring recommendation (Strong Match, Potential Match, Weak Match).

### 3.4 API Endpoints (`src/api/routes/parser.py`)
- `POST /api/v1/parse`: Upload resume file (multipart/form-data) $\rightarrow$ `CandidateProfile`.
- `POST /api/v1/score`: Send parsed profile + job description $\rightarrow$ `ATSScoreReport`.
- `POST /api/v1/analyze`: Upload resume file + job description form field $\rightarrow$ `CandidateProfile` + `ATSScoreReport`.
- `GET /api/v1/health`: Server status, active parser mode (`heuristic` or `llm`), and version.

### 3.5 Anti-AI Slop Workstation UI (`src/static/`)
- Technical workstation with a clean dark theme.
- **Left Panel (Inputs)**:
  - Drag-and-drop resume upload box.
  - Job description textarea with sample presets (*Frontend Lead*, *Python Backend Engineer*, *Fullstack Dev*).
  - Engine mode selector & live timing indicator.
  - Run button with keyboard shortcut (`Ctrl+Enter`).
- **Right Panel (Output)**:
  - Candidate header card (name, contact, links).
  - Prominent ATS score circular gauge with color-coded status (green $\ge 75$, amber $50-74$, red $< 50$).
  - Strengths and Gaps cards.
  - Tabs:
    - *Profile*: Work experience timeline, categorized skills tags, education cards.
    - *Scorecard*: Detailed score breakdown by rubric category.
    - *Raw JSON*: Syntax-highlighted JSON viewer with a one-click copy button.

### 3.6 Strictly Phase-Wise Study Documentation (`study_docs/`)
The learning documentation is explicitly divided into dedicated phase documents (not date logs or calendar entries) so you can understand the system in depth:
- `study_docs/README.md`: Master table of contents, high-level architecture diagram, and phase guide.
- `study_docs/phase-1.md`: **Phase 1 — Document Ingestion & Text Normalizer** (Multi-format readers for PDF/DOCX/TXT, encoding cleanups, section boundary detection). Includes Layman Analogy + Technical Architecture + File-by-File breakdown.
- `study_docs/phase-2.md`: **Phase 2 — Candidate Entity Extraction Engine** (Pydantic models, offline regex & token heuristics, LLM structured extraction prompt). Includes Layman Analogy + Technical Architecture + File-by-File breakdown.
- `study_docs/phase-3.md`: **Phase 3 — Rubric-Based ATS Matcher & Gap Analysis** (Weighted scoring algorithms for skills, experience, education, gap detection, strength synthesis). Includes Layman Analogy + Technical Architecture + File-by-File breakdown.
- `study_docs/phase-4.md`: **Phase 4 — REST API Endpoints & Workstation UI** (FastAPI service architecture, static mount, reactive dual-panel workstation mechanics). Includes Layman Analogy + Technical Architecture + File-by-File breakdown.

---

## 4. Dead Code & Bloat Audit

| File / Component in `hiring2` | Action | Rationale |
| :--- | :--- | :--- |
| `src/services/bill_classification.py`, `test_bill.jpg` | Purged | Receipt classification is out-of-scope for an ATS. |
| `service_old_backup.py`, `providers_v1.py` | Purged | Stale backup copies. |
| Multiple vector stores (`vector_store_FAISS.py`, `vector_store_Mongo.py`, etc.) | Decoupled | Hard MongoDB Atlas vector database dependencies removed for lightweight local run. |
| `meeting.py`, `transcript_workflow.py`, `bot.py` | Purged | Zoom/Teams interview bot recorder is irrelevant to resume parsing. |
| `linkedin.py`, `oss_talent.py` | Purged | Unreliable external scrapers stripped out. |
| `ats_backfill.py` | Purged | Persistent PostgreSQL background worker loop removed. |
| `a.txt`, `check.py`, `run-*.json`, `list_db_jobs.py`, `.cursorrules` | Purged | Temporary developer files and old IDE rules omitted. |
| Real `.env` file | Excluded | Never copy secrets or sensitive credentials. |

---

## 5. Testing & Verification Plan

1. **Document Loading**: Verify `.pdf`, `.docx`, and `.txt` files extract raw text without error.
2. **Heuristic Extraction**: Verify full candidate extraction (name, email, skills, experience) in 100% offline mode with zero API keys.
3. **ATS Matcher**: Verify scoring returns consistent scores, breakdown percentages, strengths, and missing gaps.
4. **End-to-End API**: Test `/health`, `/parse`, `/score`, and `/analyze` via local `httpx` or `curl`.
5. **Workstation UI**: Verify in-browser loading, drag-and-drop file upload, tab switching, and JSON copy functionality.
6. **Documentation**: Verify all `study_docs/` files are complete with layman and technical sections.
