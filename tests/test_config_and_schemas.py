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
        contact=ContactInfo(name="Jane Doe", email="jane@example.com", phone="+1-234-567-8901"),
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
    assert profile.contact.phone == "+1-234-567-8901"
    assert len(profile.skills) == 3
    assert profile.experience[0].company == "TechCorp"

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
    assert report.match_level == "Strong Match"
    assert "technical_skills" in report.categories
