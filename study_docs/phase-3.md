# Phase 3: Rubric-Based ATS Matcher & Gap Analysis

**Author:** saswa  
**Status:** `🟢 Completed`  
**Focus:** Comparing extracted candidate credentials against target job descriptions using weighted multi-category rubric scoring and automated gap detection.

---

## 💡 Layman's Analogy (Explain Like I'm 5)

Imagine you are looking to hire a head chef for an Italian restaurant. You have a checklist of what you need:
1. Must know how to make homemade pasta and sourdough (Crucial skill: 40% importance).
2. Must have at least 4 years of experience running a commercial kitchen (Experience: 35% importance).
3. Culinary school diploma (Education: 15% importance).
4. Clean references, organized menu presentation (Quality: 10% importance).

When an applicant's resume comes in:
- A junior recruiter might say: *"They made pasta once in 2020, looks good!"*
- A great senior manager uses a **Scoring Rubric**: they calculate the exact percentage match, praise what the applicant does exceptionally well (**Key Strengths**), and list what they are missing (**Critical Gaps**, e.g., *"They've never managed kitchen inventory or cooked on a wood-fired pizza oven"*).

**Phase 3 is that Senior Hiring Manager:**
It takes the structured candidate profile from Phase 2, compares it to any job description you paste in, computes an objective match score (0 to 100%), and writes a recruiter-ready executive summary.

---

## 🛠️ Technical Architecture & Mathematical Formulation

The matching engine in `src/engine/matcher.py` executes a 4-tier weighted evaluation:

$$\text{Overall ATS Score} = \sum_{i \in \text{Categories}} (w_i \cdot S_i)$$

Where:
- $w_{\text{skills}} = 0.40$ (Technical Skills match)
- $w_{\text{exp}} = 0.35$ (Years of Experience & Job Title alignment)
- $w_{\text{edu}} = 0.15$ (Highest degree credentials)
- $w_{\text{qual}} = 0.10$ (Resume completeness, contact verification, metrics)

```mermaid
graph TD
    A[CandidateProfile from Phase 2] --> M[ATSMatcher.evaluate]
    B[Job Description Text] --> M
    
    M --> C[Skills Matcher 40%]
    M --> D[Experience Matcher 35%]
    M --> E[Education Matcher 15%]
    M --> F[Quality Scorer 10%]
    
    C --> G[Weighted Aggregator]
    D --> G
    E --> G
    F --> G
    
    G --> H[Overall ATS Score 0-100%]
    G --> I[Match Level: Strong >=75 | Potential 50-74 | Weak <50]
    G --> J[Key Strengths Synthesis]
    G --> K[Critical Gaps & Missing Skills]
    G --> L[Recruiter Recommendation]
```

---

## 📄 File Breakdown & Responsibilities

### `src/engine/matcher.py`
- **Layman summary**: The referee that scores the candidate against the job description and highlights the strengths and weaknesses.
- **Technical specifications**:
  - **Keyword & Entity Extraction from Job Description**: Uses the taxonomy engine to dynamically harvest target skills mentioned in the job post text without requiring pre-tagged input schemas.
  - **Set Intersection & Recall Calculation**:
    - Calculates technical match ratio: $|S_{\text{matched}}| / |S_{\text{required}}|$.
    - Identifies `matched_skills` and `missing_skills`.
    - Awards domain breadth bonuses for complementary engineering skills.
  - **Tenure & Title Scoring**:
    - Parses required experience years from strings like `4+ years of professional backend experience`.
    - Compares candidate's `total_experience_years` with required threshold. If candidate meets or exceeds threshold, awards $90.0 - 100.0$ score; scales proportionally if candidate is below.
    - Evaluates role title token similarity (e.g. matching `Senior Backend Engineer` with `Backend Engineer`).
  - **Academic Degree Hierarchy**:
    - Evaluates requirements for Bachelor's, Master's, or Ph.D. degrees and compares candidate's verified institutions and degrees.
  - **Gap & Strength Synthesis**:
    - Automated detection of missing technologies (e.g. *"Missing mentions of key technologies: Kubernetes, Kafka"*).
    - Highlights standout qualifications (e.g. *"Solid career experience (5+ years) in Backend Engineering"*).
  - **Recruiter Action Recommendation**:
    - Generates actionable next-step directives: *"Recommended to advance immediately to technical interview"* vs *"Recommended for initial recruiter screening call"* vs *"Recommend reviewing alternative roles"*.

---

## 🧪 Verification & How to Test This Phase

Run the Phase 3 test suite:

```bash
python -m pytest tests/test_matcher.py -v
```

**Test Coverage Criteria:**
- Verifies overall score calculation against realistic job requirements.
- Verifies technical skill set overlap (`Python`, `FastAPI`, `PostgreSQL` recognized as matched).
- Verifies gap detection identifies missing keywords (`Kubernetes`, `Kafka`).
- Verifies graceful handling when an empty job description is passed (returns neutral 50% baseline without error).
