# SDD ledger — plan: docs/superpowers/plans/2026-10-01-ats-resume-parser.md

Pre-flight: Interfaces scanned.
- Task 1 produces `settings`, `CandidateProfile`, `ATSScoreReport` -> Consumed by Tasks 2, 3, 4, 5. Clean.
- Task 2 produces `DocumentLoader`, `TextNormalizer`, `NormalizedDocument` -> Consumed by Task 3. Clean.
- Task 3 produces `CandidateExtractor` -> Consumed by Tasks 4, 5. Clean.
- Task 4 produces `ATSMatcher` -> Consumed by Task 5. Clean.
- Task 5 produces FastAPI application, API routes, and static workstation UI -> Tested in Task 5.
- Task 6 produces finalized documentation and master README. Clean.
