---
name: phase-doc-sync
description: "Automatically synchronizes and enhances study documentation in study_docs/ whenever code in src/ or tests/ is added, updated, or refactored. Keeps educational walk-throughs, architecture diagrams, and concepts 100% in sync with code reality."
---

# Phase Documentation Synchronization & Learning Engine

## Purpose
This skill ensures that `study_docs/` in the `parse ATS` repository is never an outdated afterthought. Whenever code in `src/` or `tests/` is modified, added, or refactored, the subsequent phase documentation must immediately be updated to reflect:
1. What changed and why.
2. The core Computer Science and Software Engineering concepts utilized.
3. A file-by-file breakdown of mechanics and algorithms.
4. "Skill-Up" takeaways so developers reading the docs can level up their skills.

---

## Phase Mapping Matrix

Whenever a file is touched, refer to this mapping to know which phase document to update:

| Modified Code Paths | Target Phase Documentation | Core Concepts |
| :--- | :--- | :--- |
| `src/parser/loader.py` | `study_docs/phase-1.md` | Spatial Layout Ingestion, PyMuPDF Block Geometries, 2-Column Bounding Boxes, Scanned PDF OCR Detection. |
| `src/parser/splitter.py`, `src/core/config.py` (DocJev settings) | `study_docs/phase-2.md` | Document Packet Splitting, DocJev / TypeSafe Jev Decision Models vs LLMs, Page-Range Boundary Detection, Document Gatekeeping. |
| `src/parser/normalizer.py`, `src/engine/heuristics.py` | `study_docs/phase-3.md` | Fuzzy Section Normalization, 80+ Multilingual Aliases, Unicode NFC vs NFKD Composition, DFA & Regex Boundary Anchors. |
| `src/engine/extractor.py`, `src/core/llm.py`, `src/engine/matcher.py`, `src/api/` | `study_docs/phase-4.md` | Neuro-Symbolic Hybrid Reconciliation, Zero-Hallucination Grounding, 4-Tier Rubric Matching, FastAPI REST endpoints. |
| Architecture-wide or multi-layer changes | `study_docs/README.md` | Master System Architecture, Flowcharts, Phase Table of Contents. |

---

## Pedagogical Documentation Standard

Every updated phase document must follow this educational structure:

1. **The Real-World Problem & Layman Analogy**:
   - Explain why the problem exists in industry using a vivid everyday analogy (e.g., sorting mail, comparing columned newspapers, forensic fact-checking).
2. **Computer Science Concepts Used**:
   - Detail the computational theory (e.g. 2D Bounding-Box Spatial Clustered Partitioning, Deterministic Finite Automata, Neuro-Symbolic Systems, Decision Theory).
3. **File-by-File Technical Deep Dive**:
   - List every function and class, explaining its input, output, algorithmic logic, and edge-case handling.
4. **Visual Architecture Diagram**:
   - Flowcharts (`mermaid`) illustrating how data transforms step-by-step.
5. **Skill-Up Takeaways for Your Career**:
   - Practical engineering principles you can cite in system design interviews or apply to future enterprise AI systems.

---

## Execution Workflow

1. **Detect Changes**:
   - Run `git status` or inspect recent file modifications in `src/` and `tests/`.
2. **Identify Target Phase Doc**:
   - Check the Phase Mapping Matrix above.
3. **Inspect the Diff & Logic**:
   - Examine the new inputs, outputs, error handles, and edge cases.
4. **Update Phase Document**:
   - Preserve previous foundational knowledge while seamlessly integrating the new mechanisms, code snippets, and conceptual breakdowns.
5. **Update Master README**:
   - If new layers or endpoints were introduced, update `study_docs/README.md` to keep the master system map synchronized.
