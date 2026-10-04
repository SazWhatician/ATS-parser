"""Candidate profile extractor coordinating neuro-symbolic hybrid extraction."""

import logging
import re
from typing import Optional, Dict, Any, List
from src.parser.normalizer import NormalizedDocument
from src.api.schemas.candidate import CandidateProfile, ContactInfo, ExperienceItem
from src.engine.heuristics import HeuristicResumeParser
from src.core.llm import llm_client

logger = logging.getLogger(__name__)


class CandidateExtractor:
    """Extracts structured candidate data using an adaptive Neuro-Symbolic Hybrid engine.
    
    Combines deterministic ground-truth heuristics (regex contact verification, taxonomy matching)
    with deep semantic LLM reasoning (complex timeline understanding, implicit skills, narrative synthesis).
    """

    def __init__(self, force_heuristic: bool = False):
        self.force_heuristic = force_heuristic

    def extract(self, doc: NormalizedDocument) -> CandidateProfile:
        """Extract candidate profile using adaptive hybrid reconciliation."""
        if not doc.clean_text:
            return CandidateProfile(extraction_mode="heuristic")

        # 1. Deterministic Heuristic Ground Truth Pass
        heuristic_profile = HeuristicResumeParser.parse(doc)

        # If forced or no LLM key configured, return heuristic directly
        if self.force_heuristic or not llm_client.is_available:
            return heuristic_profile

        # 2. Semantic LLM Pass
        try:
            llm_result = self._extract_with_llm(doc)
            if llm_result:
                # 3. Hybrid Reconciliation Pass
                return self._reconcile(heuristic_profile, llm_result, doc)
        except Exception as e:
            logger.warning(f"LLM extraction error: {e}. Gracefully falling back to deterministic heuristics.")

        return heuristic_profile

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
{doc.clean_text[:14000]}
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

        raw_json["extraction_mode"] = "llm"
        raw_json["raw_text_preview"] = doc.clean_text[:300] + "..."
        return CandidateProfile(**raw_json)

    def _reconcile(
        self,
        heuristic: CandidateProfile,
        llm: CandidateProfile,
        doc: NormalizedDocument
    ) -> CandidateProfile:
        """Reconcile deterministic heuristics with LLM semantic inferences (Neuro-Symbolic Fusion)."""
        clean_text_lower = doc.clean_text.lower()

        # 1. Contact Info Reconciliation
        # Heuristic email and phone are regex-verified against actual text
        reconciled_email = llm.contact.email
        if not reconciled_email or reconciled_email.lower() not in clean_text_lower:
            # Revert to ground-truth heuristic if LLM hallucinated or missed
            reconciled_email = heuristic.contact.email

        reconciled_phone = llm.contact.phone or heuristic.contact.phone
        reconciled_name = llm.contact.name
        # Guard against placeholder names
        if not reconciled_name or reconciled_name.lower() in ["full name", "candidate", "name"]:
            reconciled_name = heuristic.contact.name

        reconciled_contact = ContactInfo(
            name=reconciled_name,
            email=reconciled_email,
            phone=reconciled_phone,
            location=llm.contact.location or heuristic.contact.location,
            linkedin=llm.contact.linkedin or heuristic.contact.linkedin,
            github=llm.contact.github or heuristic.contact.github,
            portfolio=llm.contact.portfolio or heuristic.contact.portfolio
        )

        # 2. Skills Fusion (Union of LLM inferred skills + Heuristic taxonomy matches)
        combined_skills_set = set()
        cased_skills: List[str] = []

        # Add LLM skills first
        for s in (llm.skills or []):
            if s and s.strip() and s.lower() not in combined_skills_set:
                combined_skills_set.add(s.lower())
                cased_skills.append(s.strip())

        # Fuse heuristic taxonomy skills (catches anything the LLM overlooked)
        for s in (heuristic.skills or []):
            if s and s.strip() and s.lower() not in combined_skills_set:
                combined_skills_set.add(s.lower())
                cased_skills.append(s.strip())

        # Merge categorized skills
        merged_categorized: Dict[str, List[str]] = dict(llm.categorized_skills or {})
        for cat, skills in (heuristic.categorized_skills or {}).items():
            if cat not in merged_categorized:
                merged_categorized[cat] = skills
            else:
                existing_set = {sk.lower() for sk in merged_categorized[cat]}
                for sk in skills:
                    if sk.lower() not in existing_set:
                        merged_categorized[cat].append(sk)
                        existing_set.add(sk.lower())

        # 3. Experience & Timeline Reconciliation
        experience = llm.experience if llm.experience else heuristic.experience
        total_exp = llm.total_experience_years if (llm.total_experience_years and llm.total_experience_years > 0) else heuristic.total_experience_years

        # 4. Education, Projects, and Certifications
        education = llm.education if llm.education else heuristic.education
        projects = llm.projects if llm.projects else heuristic.projects
        certifications = llm.certifications if llm.certifications else heuristic.certifications

        return CandidateProfile(
            contact=reconciled_contact,
            summary=llm.summary or heuristic.summary,
            total_experience_years=total_exp,
            primary_domain=llm.primary_domain or heuristic.primary_domain,
            skills=sorted(cased_skills),
            categorized_skills=merged_categorized,
            experience=experience,
            education=education,
            projects=projects,
            certifications=certifications,
            raw_text_preview=heuristic.raw_text_preview,
            extraction_mode="hybrid"
        )
