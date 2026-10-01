# ATS Resume Parser & Rubric Evaluation Engine

<p align="left">
  <strong>Author & Maintainer:</strong> <a href="https://github.com/saswa">saswa</a><br>
  <strong>Engine Mode:</strong> Dual Execution (100% Local Offline Heuristic + LLM Enhanced)<br>
  <strong>Interface:</strong> Embedded Anti-AI Slop Workstation + REST API
</p>

---

## 🌟 Overview

The **ATS Resume Parser & Evaluation Engine** is a high-performance, local-first Applicant Tracking System component designed to parse unstructured candidate resumes (`.pdf`, `.docx`, `.txt`), extract structured candidate profiles, and evaluate them against target job descriptions using a rigorous, multi-factor scoring rubric.

Built from the ground up with clean architecture, zero code bloat, and strict input validation, this project eliminates heavy external cloud database locks and runs completely offline with **zero API keys** required by default.

---

## 🚀 Key Highlights

- **🛡️ 100% Local-First & Zero-Key Resilience**:
  - The deterministic **Heuristic Engine** runs locally with zero external network calls and zero cost. It parses candidate identity, emails, phone numbers, social links, technical skill taxonomies (200+ technologies), chronological work history, and academic credentials in milliseconds.
  - Optional **LLM Mode**: Plug in your OpenRouter, Google Gemini, or OpenAI API key in `.env` to activate deep semantic reasoning with automatic fallback to heuristics if the network or credits drop.
- **📄 Universal Document Ingestion**:
  - Multi-engine PDF decoding (PyMuPDF `fitz` primary with `pdfplumber` fallback).
  - Table-aware Microsoft Word `.docx` parsing via `python-docx`.
  - Multi-encoding `.txt` decoding (`utf-8`, `latin-1`, `cp1252`).
- **⚖️ 4-Tier Rubric Scoring System**:
  - **Technical Skills Match (40% weight)**: Required vs. nice-to-have skill overlaps.
  - **Experience & Role Relevance (35% weight)**: Tenure calculations and title alignment.
  - **Academic Degree Credentials (15% weight)**: Highest degree validation.
  - **Document Presentation Quality (10% weight)**: Contact completeness and achievement metrics.
  - Automatically synthesizes **Key Strengths**, **Critical Gaps / Missing Keywords**, and a tailored **Recruiter Action Directive**.
- **💻 Anti-AI Slop Workstation UI**:
  - Executive dark-mode workbench built with pure HTML5, modern CSS, and vanilla JavaScript (zero `npm` or `node_modules` required).
  - Drag-and-drop resume upload zone, instant job description presets (*Backend Lead*, *Frontend Eng*, *ML Specialist*), interactive timeline tabs, categorized skill chips, and a syntax-highlighted raw JSON viewer with one-click clipboard copy.

---

## 📂 System Architecture

```text
parse ATS/
├── study_docs/                    # Strictly Phase-Wise Learning Docs (Layman + Technical)
│   ├── README.md                  # Master Index & Architecture Map
│   ├── phase-1.md                 # Phase 1: Core Document Ingestion & Text Normalizer
│   ├── phase-2.md                 # Phase 2: Entity Extraction Engine (Heuristic + LLM)
│   ├── phase-3.md                 # Phase 3: Rubric ATS Scoring & Gap Analysis Engine
│   └── phase-4.md                 # Phase 4: REST API & Interactive Workstation UI
├── src/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── parser.py          # Endpoints: /parse, /score, /analyze
│   │   │   └── health.py          # Endpoints: /health
│   │   ├── schemas/
│   │   │   ├── candidate.py       # Pydantic schemas for candidate profiles
│   │   │   └── matching.py        # Pydantic schemas for ATS score reports
│   │   └── router.py              # Consolidated v1 router
│   ├── core/
│   │   ├── config.py              # Application settings (zero leaked keys)
│   │   └── llm.py                 # Multi-provider client (OpenRouter, Gemini, OpenAI)
│   ├── engine/
│   │   ├── heuristics.py          # Deterministic offline regex & taxonomy extractor
│   │   ├── extractor.py           # Extraction coordinator (Heuristic + LLM)
│   │   └── matcher.py             # 4-tier rubric matcher & gap synthesizer
│   ├── parser/
│   │   ├── loader.py              # Universal document loader (PDF, DOCX, TXT)
│   │   └── normalizer.py          # Text sanitization, unicode NFKD, and section chunking
│   ├── static/
│   │   ├── index.html             # Sleek dark-mode workstation dashboard
│   │   ├── styles.css             # Anti-AI slop dark theme
│   │   └── app.js                 # Workstation client logic & state management
│   ├── main.py                    # FastAPI server entrypoint
│   └── __init__.py
├── .env.example                   # Environment configuration template
├── .gitignore                     # Git hygiene rules
├── pyproject.toml                 # Modern package configuration
├── requirements.txt               # Pinned dependencies
└── README.md                      # Primary project documentation
```

---

## ⚡ Quickstart Guide

### 1. Prerequisites
- Python 3.10 or higher.
- UV or pip package manager.

### 2. Installation
```bash
# Clone the repository locally
git clone <local-repo-path>
cd "parse ATS"

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Launch the Workstation & API
```bash
python src/main.py
```
Or with Uvicorn directly:
```bash
uvicorn src.main:app --reload --port 8000
```

Once running:
- **Interactive Workstation UI**: Open [http://localhost:8000/](http://localhost:8000/) in your browser.
- **Interactive Swagger Docs**: Open [http://localhost:8000/docs](http://localhost:8000/docs).

---

## 🧪 Testing

The repository comes with a comprehensive test suite covering document loading, normalization, heuristic extraction, rubric scoring, and API route execution.

```bash
python -m pytest tests/ -v
```

---

## 📡 API Reference

### 1. Health & Diagnostics
- **Method:** `GET`
- **URL:** `/api/v1/health`
- **Response:**
```json
{
  "status": "healthy",
  "app_name": "ATS Resume Parser & Match Engine",
  "version": "1.0.0",
  "author": "saswa",
  "engine_mode": "heuristic",
  "has_llm_key": false,
  "supported_formats": [".pdf", ".docx", ".txt"]
}
```

### 2. Parse Resume
- **Method:** `POST`
- **URL:** `/api/v1/parse`
- **Body:** `multipart/form-data` with `file: <resume_file>`
- **Response:** Full structured `CandidateProfile` JSON.

### 3. Evaluate & Match Candidate
- **Method:** `POST`
- **URL:** `/api/v1/analyze`
- **Body:** `multipart/form-data`
  - `file`: Resume file (`.pdf`, `.docx`, `.txt`)
  - `job_description`: *(Optional)* Target job text.
  - `force_heuristic`: *(Optional, boolean)* Defaults to `false`.
- **Response Sample:**
```json
{
  "profile": {
    "contact": {
      "name": "Jane Developer",
      "email": "jane@example.com",
      "phone": "+1-555-0199",
      "location": "San Francisco, CA",
      "github": "github.com/janedev"
    },
    "skills": ["Docker", "FastAPI", "PostgreSQL", "Python", "Redis"],
    "experience": [...],
    "education": [...]
  },
  "score_report": {
    "overall_score": 88.5,
    "match_level": "Strong Match",
    "recommendation": "Jane Developer is a high-confidence match (88.5%) for this role. Recommended to advance immediately to technical interview.",
    "categories": {
      "technical_skills": { "score": 92.0, "weight": 0.4 },
      "experience": { "score": 85.0, "weight": 0.35 },
      "education": { "score": 90.0, "weight": 0.15 },
      "quality": { "score": 80.0, "weight": 0.1 }
    },
    "strengths": [
      "Strong match on core tech stack: Python, FastAPI, PostgreSQL, Docker.",
      "Solid career experience (5+ years) in Backend Engineering."
    ],
    "gaps": [
      "Missing mentions of key technologies: Kubernetes, Kafka."
    ]
  },
  "processing_time_ms": 12.4,
  "engine_mode": "heuristic"
}
```

---

## 📚 Phase-Wise Study Documentation

For an educational, in-depth explanation of every single phase and file in the codebase, consult the dedicated study documents:

1. [Phase 1: Core Document Ingestion & Text Normalizer](file:///c:/Users/saswa/Desktop/parse%20ATS/study_docs/phase-1.md)
2. [Phase 2: Candidate Entity Extraction Engine](file:///c:/Users/saswa/Desktop/parse%20ATS/study_docs/phase-2.md)
3. [Phase 3: Rubric ATS Matcher & Gap Analysis Engine](file:///c:/Users/saswa/Desktop/parse%20ATS/study_docs/phase-3.md)
4. [Phase 4: REST API Endpoints & Workstation UI](file:///c:/Users/saswa/Desktop/parse%20ATS/study_docs/phase-4.md)
5. [Master Index](file:///c:/Users/saswa/Desktop/parse%20ATS/study_docs/README.md)

---

## 👤 Author & Credits

Developed and authored by **saswa** (SazWhatician).
All rights reserved. Free for local research, personal use, and portfolio demonstrations.
