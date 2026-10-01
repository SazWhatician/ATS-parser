import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

SAMPLE_RESUME_TEXT = b"""Jane Developer
Email: jane@test.com | Phone: +1-555-0199
Location: San Francisco, CA

SUMMARY
Backend engineer with 4 years experience in Python and FastAPI.

SKILLS
Python, FastAPI, Docker, PostgreSQL

EXPERIENCE
Senior Developer | Tech Innovators | 2021 - Present
- Built scalable backend microservices using FastAPI.
"""

def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "engine_mode" in data
    assert data["author"] == "saswa"


def test_parse_endpoint():
    files = {"file": ("resume.txt", SAMPLE_RESUME_TEXT, "text/plain")}
    response = client.post("/api/v1/parse", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["contact"]["name"] == "Jane Developer"
    assert data["contact"]["email"] == "jane@test.com"
    assert "Python" in data["skills"]
    assert "FastAPI" in data["skills"]


def test_analyze_endpoint():
    files = {"file": ("resume.txt", SAMPLE_RESUME_TEXT, "text/plain")}
    form_data = {
        "job_description": "We are seeking a Python Backend Engineer with FastAPI and Docker experience."
    }
    response = client.post("/api/v1/analyze", files=files, data=form_data)
    assert response.status_code == 200
    result = response.json()
    assert "profile" in result
    assert "score_report" in result
    assert result["profile"]["contact"]["name"] == "Jane Developer"
    assert result["score_report"]["overall_score"] >= 60.0
    assert "FastAPI" in result["score_report"]["matched_skills"]


def test_invalid_extension():
    files = {"file": ("resume.exe", b"binarycontent", "application/octet-stream")}
    response = client.post("/api/v1/parse", files=files)
    assert response.status_code == 415
    assert "Unsupported file extension" in response.json()["detail"]


def test_root_serves_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "ATS Resume Parser" in response.text
