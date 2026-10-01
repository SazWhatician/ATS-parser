import pytest
from src.parser.normalizer import TextNormalizer
from src.engine.extractor import CandidateExtractor
from src.engine.matcher import ATSMatcher
from src.api.schemas.matching import ATSScoreReport
from tests.test_extractor import SAMPLE_RESUME

SAMPLE_JD = """
Job Title: Senior Python Backend Engineer
Location: San Francisco, CA

About the Role:
We are seeking an experienced Backend Engineer to lead API development and database optimization.

Requirements:
- 4+ years of professional backend software engineering experience.
- Expert knowledge of Python and FastAPI or Django.
- Hands-on experience with PostgreSQL and Redis caching.
- Proficiency with Docker and AWS or GCP cloud platforms.
- Bachelor's degree in Computer Science or equivalent.

Nice to Have:
- Experience with Kubernetes and Kafka.
- Familiarity with TypeScript and Go.
"""

def test_ats_matcher_evaluation():
    norm_doc = TextNormalizer.normalize(SAMPLE_RESUME)
    profile = CandidateExtractor(force_heuristic=True).extract(norm_doc)

    matcher = ATSMatcher()
    report = matcher.evaluate(profile, SAMPLE_JD)

    assert isinstance(report, ATSScoreReport)
    assert report.overall_score >= 70.0
    assert report.match_level in ["Strong Match", "Potential Match"]
    assert "technical_skills" in report.categories
    assert "experience" in report.categories
    assert "education" in report.categories
    assert "quality" in report.categories
    assert report.categories["technical_skills"].score >= 75.0
    assert len(report.strengths) > 0
    # Jane doesn't have Kubernetes or Kafka in SAMPLE_RESUME
    assert any("Kubernetes" in gap or "Kafka" in gap for gap in report.gaps)
    assert "Python" in report.matched_skills
    assert "FastAPI" in report.matched_skills
    assert "PostgreSQL" in report.matched_skills


def test_ats_matcher_empty_jd():
    norm_doc = TextNormalizer.normalize(SAMPLE_RESUME)
    profile = CandidateExtractor(force_heuristic=True).extract(norm_doc)

    matcher = ATSMatcher()
    report = matcher.evaluate(profile, "")

    assert isinstance(report, ATSScoreReport)
    assert report.overall_score == 50.0
    assert "No job description provided" in report.recommendation
