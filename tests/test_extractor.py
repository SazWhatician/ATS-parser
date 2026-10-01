import pytest
from src.parser.normalizer import TextNormalizer
from src.engine.extractor import CandidateExtractor
from src.api.schemas.candidate import CandidateProfile

SAMPLE_RESUME = """
Jane Developer
Email: jane.dev@example.com | Phone: +1-555-0199 | Location: San Francisco, CA
LinkedIn: linkedin.com/in/janedev | GitHub: github.com/janedev

SUMMARY
Seasoned backend engineer with 5 years of experience in distributed systems.

TECHNICAL SKILLS
Languages: Python, Go, TypeScript, SQL
Frameworks: FastAPI, Django, React
Infrastructure: Docker, AWS, PostgreSQL, Redis

WORK EXPERIENCE
Senior Backend Engineer | Acme Innovations | 2021 - Present
- Architected high-throughput microservices using FastAPI and Redis.
- Reduced database query latency by 40% using PostgreSQL indexing.

Software Engineer | Beta Corp | 2019 - 2021
- Developed REST APIs and background worker pipelines in Python.

EDUCATION
B.S. in Computer Science | University of California, Berkeley | 2015 - 2019
"""

def test_heuristic_offline_extraction():
    norm_doc = TextNormalizer.normalize(SAMPLE_RESUME)
    extractor = CandidateExtractor(force_heuristic=True)
    profile = extractor.extract(norm_doc)

    assert isinstance(profile, CandidateProfile)
    assert profile.contact.name == "Jane Developer"
    assert profile.contact.email == "jane.dev@example.com"
    assert "555-0199" in (profile.contact.phone or "")
    assert "github.com/janedev" in (profile.contact.github or "")
    assert "linkedin.com/in/janedev" in (profile.contact.linkedin or "")
    assert "Python" in profile.skills
    assert "FastAPI" in profile.skills
    assert "Docker" in profile.skills
    assert len(profile.experience) >= 2
    assert any("Acme" in exp.company for exp in profile.experience)
    assert any("Senior Backend Engineer" in exp.role for exp in profile.experience)
    assert len(profile.education) >= 1
    assert "Berkeley" in profile.education[0].institution or "Computer Science" in (profile.education[0].degree or "")
    assert profile.extraction_mode == "heuristic"


def test_heuristic_empty_resume():
    norm_doc = TextNormalizer.normalize("")
    extractor = CandidateExtractor(force_heuristic=True)
    profile = extractor.extract(norm_doc)
    assert profile.contact.name is None
    assert profile.skills == []
    assert profile.experience == []
