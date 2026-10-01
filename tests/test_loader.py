import pytest
from pathlib import Path
from src.parser.loader import DocumentLoader, LoadedDocument
from src.parser.normalizer import TextNormalizer, NormalizedDocument


def test_plain_text_loading(tmp_path):
    sample_txt = tmp_path / "resume.txt"
    sample_txt.write_text(
        "John Doe\nSoftware Engineer\nSkills: Python, FastAPI\nExperience:\nAcme Corp - 2 years",
        encoding="utf-8"
    )
    
    doc = DocumentLoader.load_file(sample_txt)
    assert isinstance(doc, LoadedDocument)
    assert "John Doe" in doc.raw_text
    assert doc.file_type == "txt"
    assert doc.page_count == 1


def test_bytes_loading():
    content = b"Candidate: Alice Smith\nSkills: Go, Docker\nEducation: B.S. in CS"
    doc = DocumentLoader.load_bytes(content, filename="resume.txt")
    assert "Alice Smith" in doc.raw_text
    assert doc.file_type == "txt"


def test_unsupported_file_type(tmp_path):
    bad_file = tmp_path / "resume.xyz"
    bad_file.write_text("Hello", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported file format"):
        DocumentLoader.load_file(bad_file)


def test_text_normalization():
    dirty_text = (
        "  John Doe  \r\n\r\n\tSenior Dev \xa0\xa0\n\n"
        "EXPERIENCE:\nWorked on backend systems.\n\n"
        "SKILLS:\nPython, SQL, Redis\n\n"
        "EDUCATION:\nStanford University - B.S. CS"
    )
    normalized = TextNormalizer.normalize(dirty_text)
    assert isinstance(normalized, NormalizedDocument)
    assert "John Doe" in normalized.clean_text
    assert "Senior Dev" in normalized.clean_text
    assert "experience" in normalized.sections
    assert "skills" in normalized.sections
    assert "education" in normalized.sections
    assert "Worked on backend systems." in normalized.sections["experience"]
    assert "Python, SQL, Redis" in normalized.sections["skills"]
    assert normalized.word_count > 10


def test_empty_text_normalization():
    normalized = TextNormalizer.normalize("   \n\t  ")
    assert normalized.clean_text == ""
    assert normalized.word_count == 0
    assert normalized.sections == {}
