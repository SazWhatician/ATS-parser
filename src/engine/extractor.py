"""Candidate profile extractor coordinating heuristic and LLM extraction."""

import logging
from typing import Optional, Dict, Any
from src.parser.normalizer import NormalizedDocument
from src.api.schemas.candidate import CandidateProfile
from src.engine.heuristics import HeuristicResumeParser
from src.core.llm import llm_client

logger = logging.getLogger(__name__)


class CandidateExtractor:
    """Extracts structured candidate data using heuristic rules or LLM."""

    def __init__(self, force_heuristic: bool = False):
        self.force_heuristic = force_heuristic

    def extract(self, doc: NormalizedDocument) -> CandidateProfile:
        """Extract candidate profile from normalized document."""
        if not doc.clean_text:
            return CandidateProfile(extraction_mode="heuristic")

        # 1. Use offline heuristic parser if forced or if no LLM key is configured
        if self.force_heuristic or not llm_client.is_available:
            return HeuristicResumeParser.parse(doc)

        # 2. Attempt LLM extraction when API key is present
        try:
            llm_result = self._extract_with_llm(doc)
            if llm_result:
                return llm_result
        except Exception as e:
            logger.warning(f"LLM extraction encountered an error: {e}. Falling back to heuristic engine.")

        # 3. Graceful fallback to heuristic
        return HeuristicResumeParser.parse(doc)

    def _extract_with_llm(self, doc: NormalizedDocument) -> Optional[CandidateProfile]:
        """Perform structured extraction using LLM."""
        system_prompt = (
            "You are an expert ATS (Applicant Tracking System) entity extraction model. "
            "Extract structured candidate details strictly adhering to the JSON schema. "
            "Do not fabricate details not present in the resume."
        )

        prompt = f"""
Parse the following resume into JSON format:

RESUME TEXT:
\"\"\"
{doc.clean_text[:12000]}
\"\"\"

Return a valid JSON object matching this schema:
{{
  "contact": {{
    "name": "Full Name",
    "email": "email@example.com",
    "phone": "+1-000-000-0000",
    "location": "City, State",
    "linkedin": "url",
    "github": "url",
    "portfolio": "url"
  }},
  "summary": "Professional summary paragraph",
  "total_experience_years": 5.0,
  "primary_domain": "Backend Engineering",
  "skills": ["Skill1", "Skill2"],
  "categorized_skills": {{"Languages": ["Python"], "Frameworks": ["FastAPI"]}},
  "experience": [
    {{
      "company": "Company Name",
      "role": "Job Title",
      "location": "Location",
      "duration": "2 years",
      "start_date": "2021",
      "end_date": "Present",
      "highlights": ["Bullet point 1"],
      "technologies": ["Python", "Docker"]
    }}
  ],
  "education": [
    {{
      "institution": "University Name",
      "degree": "B.S. in CS",
      "field_of_study": "Computer Science",
      "graduation_year": "2020"
    }}
  ],
  "projects": [],
  "certifications": []
}}
"""

        raw_json = llm_client.generate_json(prompt, system_prompt)
        if not raw_json:
            return None

        # Validate with Pydantic
        raw_json["extraction_mode"] = "llm"
        raw_json["raw_text_preview"] = doc.clean_text[:300] + "..."
        return CandidateProfile(**raw_json)
