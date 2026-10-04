# Phase 2: Document Packet Boundary Splitting & Classification

**Author:** SazWhatician  
**Status:** `🟢 Completed & Upgraded`  
**Layer in System:** **Layer 2: Document Segmentation & Packet Splitting**  
**Core Files:** [`src/parser/splitter.py`](file:///c:/Users/saswa/Desktop/parse%20ATS/src/parser/splitter.py), [`src/core/config.py`](file:///c:/Users/saswa/Desktop/parse%20ATS/src/core/config.py)

---

## 💡 Layman's Analogy (Explain Like I'm 5)

Imagine an applicant sends you an envelope. Inside the envelope is not just a resume: they also included a **1-page Cover Letter**, a **2-page Resume**, and a **3-page University Transcript** with semester grades.

If you blindly throw all 6 pages into an ATS parser, the parser gets confused:
- It mistakes the university registrar's name on the transcript for the candidate's boss!
- It mistakes the cover letter pitch for work experience!
- It counts courses on the transcript as years of job tenure!

Or worse: a recruiting agency dumps a single 30-page PDF containing **10 different candidates** scanned together!

**Phase 2 is your Expert Packet Inspector:**
1. It looks through the pages of the packet.
2. It detects where the **Cover Letter** ends and where the **Resume** begins.
3. It detects where the **Transcripts** start and isolates them.
4. It cuts the document cleanly into labeled segments and extracts **strictly the actual resume** to pass downstream, discarding irrelevant attachments.
5. If someone mistakenly uploads an invoice or an office memo, it acts as a **Gatekeeper** and flags it before wasting time or money!

---

## 🎓 Computer Science Concepts Used

### 1. "System One" Decision Models vs. Generative LLMs (DocJev Architecture)
For tasks like document boundary detection and classification, using a massive general-purpose LLM (like GPT-4o or Claude 3.5 Sonnet) is:
- **Excessively slow** ($5\text{s} - 15\text{s}$ per document).
- **Expensive** (charging for thousands of generated output tokens).
- **Prone to drift** (unpredictable free-form markdown).

[`src/parser/splitter.py`](file:///c:/Users/saswa/Desktop/parse%20ATS/src/parser/splitter.py) incorporates the **DocJev philosophy** (created by Jerry Liu, cofounder of LlamaIndex) using **Jev** from **TypeSafe** (`api.typesafe.ai/v1/systemone`):
- Instead of open-ended text generation, a "System One" decision model evaluates structured category rules against document page previews in parallel.
- Execution latency drops to a fraction of traditional LLMs ($\sim 6\times$ faster).

### 2. Contiguous Interval Partitioning & State Transition Logic
When evaluating multi-page documents, each page $p \in \{1, \dots, N\}$ is assigned a category label $c_p \in \{\text{resume}, \text{cover\_letter}, \text{transcripts}, \dots\}$.
- Phase 2 applies a state-machine compression algorithm over page intervals:
  $$\text{Segment}_k = \left(c_k, \text{start\_page}, \text{end\_page}\right)$$
- Contiguous sequences of pages sharing the same predicted category are merged into coherent sub-document blocks.
- The primary resume block is isolated, while auxiliary materials are tagged and cataloged.

### 3. Dual-Engine Resilience: Cloud Decision Model with Local Fallback
In accordance with our zero-key resilience principle:
- If a `TYPESAFE_API_KEY` is present in `.env`, the system calls TypeSafe's Jev model for high-confidence boundary splitting.
- If offline or if no key is configured, [`DocumentSplitter`](file:///c:/Users/saswa/Desktop/parse%20ATS/src/parser/splitter.py#L125) executes a deterministic rule-based boundary detector that analyzes salutations (*"Dear Hiring Manager"*, *"Sincerely"*), registrar seals (*"Cumulative GPA"*, *"Official Transcript"*), and resume hallmarks.

---

## 📂 File-by-File Breakdown: `src/parser/splitter.py`

| Function / Component | Input | Output | What It Does & Edge-Case Handled |
| :--- | :--- | :--- | :--- |
| `DocumentSegment` (Dataclass) | Category, page bounds, text | Data container | Models an individual classified slice of a packet (e.g. `category="cover_letter"`, `start_page=1`, `end_page=1`). |
| `PacketSplitResult` (Dataclass) | Segment list, flags | Data container | Bundles `is_packet: bool`, `primary_category`, `primary_resume_text`, and `engine`. |
| `DocumentSplitter.process(doc)` | `LoadedDocument` | `PacketSplitResult` | **The Main Coordinator**: Bypasses splitting for single-page files; calls TypeSafe API if key configured; falls back to local heuristic boundary splitting. |
| `_split_with_typesafe(doc)` | `LoadedDocument` | `Optional[PacketSplitResult]` | Previews the first 800 characters of each page and invokes TypeSafe's Jev decision API to calculate page cut boundaries. |
| `_split_heuristically(doc)` | `LoadedDocument` | `PacketSplitResult` | Offline fallback. Evaluates per-page lexical signatures and merges contiguous category intervals without network calls. |
| `_classify_single_page(text)` | Page text string | `str` | Classifies individual page content into `resume`, `cover_letter`, `transcripts`, `job_description`, or `other`. |

---

## 🏗️ Architecture Flow Diagram

```mermaid
flowchart TD
    Doc[LoadedDocument from Phase 1] --> CheckPages{Page Count > 1?}
    
    CheckPages -- No (Single Page) --> Direct[Direct Single Page Classifier]
    Direct --> Result[PacketSplitResult: Isolate Resume Text]
    
    CheckPages -- Yes (Multi-Page Packet) --> CheckKey{TypeSafe API Key Present?}
    
    CheckKey -- Yes --> JevAPI[Call TypeSafe Jev Decision API]
    JevAPI -->|Success| Cuts[Parse Page Cuts & Categories]
    Cuts --> Stitch[Stitch Pages into Sub-Document Segments]
    
    JevAPI -- Network Failure / Timeout --> HeuristicSplit[Local Heuristic Boundary Splitter]
    CheckKey -- No (Offline Mode) --> HeuristicSplit
    
    HeuristicSplit --> Lexical[Evaluate Lexical Cues: Salutations, Registrars, Headers]
    Lexical --> Intervals[Merge Contiguous Intervals: [1-1]=Cover Letter, [2-3]=Resume]
    Intervals --> Stitch
    
    Stitch --> Filter[Filter out Non-Resume Segments]
    Filter --> Result
```

---

## 🚀 Skill-Up Takeaways for Your Career

1. **Don't use a sledgehammer for a nail (Decision Models vs Generative Models)**:
   When you only need a classification or a boundary cut, general-purpose LLMs waste massive compute generating tokens you don't need. Decision models (like Jev) return typed predictions with deterministic speed.
2. **Never assume single-document purity in enterprise ingestion**:
   Real-world enterprise users never upload "clean" single resumes. They upload email threads, agency packs, and scanned portfolios. A robust ingestion pipeline must always segment packets before running entity extraction.
3. **Always build a zero-dependency offline fallback**:
   Cloud APIs experience latency spikes and service outages. Providing an offline regex/heuristic classifier ensures your application continues processing resumes even in an airplane or isolated intranet environment.
