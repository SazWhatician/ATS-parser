"""Text normalization, section segmentation, and cleaning."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import re
import unicodedata


@dataclass
class NormalizedDocument:
    clean_text: str
    sections: Dict[str, str] = field(default_factory=dict)
    word_count: int = 0
    char_count: int = 0


class TextNormalizer:
    """Sanitizes raw resume text and segments it into semantic sections."""

    # Standard section header regex patterns
    SECTION_PATTERNS = {
        "summary": [
            r"^[\s#*=-]*professional\s+summary[\s:*=-]*$",
            r"^[\s#*=-]*executive\s+summary[\s:*=-]*$",
            r"^[\s#*=-]*career\s+summary[\s:*=-]*$",
            r"^[\s#*=-]*summary\s+of\s+qualifications[\s:*=-]*$",
            r"^[\s#*=-]*profile[\s:*=-]*$",
            r"^[\s#*=-]*about\s+me[\s:*=-]*$",
            r"^[\s#*=-]*summary[\s:*=-]*$",
        ],
        "experience": [
            r"^[\s#*=-]*work\s+experience[\s:*=-]*$",
            r"^[\s#*=-]*professional\s+experience[\s:*=-]*$",
            r"^[\s#*=-]*employment\s+history[\s:*=-]*$",
            r"^[\s#*=-]*work\s+history[\s:*=-]*$",
            r"^[\s#*=-]*experience[\s:*=-]*$",
        ],
        "education": [
            r"^[\s#*=-]*academic\s+background[\s:*=-]*$",
            r"^[\s#*=-]*academic\s+history[\s:*=-]*$",
            r"^[\s#*=-]*education\s+&\s+credentials[\s:*=-]*$",
            r"^[\s#*=-]*education[\s:*=-]*$",
        ],
        "skills": [
            r"^[\s#*=-]*technical\s+skills[\s:*=-]*$",
            r"^[\s#*=-]*core\s+competencies[\s:*=-]*$",
            r"^[\s#*=-]*skills\s+&\s+proficiencies[\s:*=-]*$",
            r"^[\s#*=-]*skills\s+&\s+abilities[\s:*=-]*$",
            r"^[\s#*=-]*technologies[\s:*=-]*$",
            r"^[\s#*=-]*skills[\s:*=-]*$",
        ],
        "projects": [
            r"^[\s#*=-]*personal\s+projects[\s:*=-]*$",
            r"^[\s#*=-]*key\s+projects[\s:*=-]*$",
            r"^[\s#*=-]*selected\s+projects[\s:*=-]*$",
            r"^[\s#*=-]*projects[\s:*=-]*$",
        ],
        "certifications": [
            r"^[\s#*=-]*licenses\s+&\s+certifications[\s:*=-]*$",
            r"^[\s#*=-]*certifications[\s:*=-]*$",
            r"^[\s#*=-]*certificates[\s:*=-]*$",
            r"^[\s#*=-]*accreditations[\s:*=-]*$",
        ],
    }

    @classmethod
    def normalize(cls, raw_text: str, max_chars: int = 50000) -> NormalizedDocument:
        """Clean raw resume text and extract known resume sections."""
        if not raw_text or not raw_text.strip():
            return NormalizedDocument(clean_text="", sections={}, word_count=0, char_count=0)

        # 1. Normalize unicode characters (NFKD replaces ligatures like 'fi', 'fl', etc.)
        text = unicodedata.normalize("NFKD", raw_text)

        # 2. Standardize non-breaking spaces, unusual spaces, and control characters
        text = text.replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")
        
        # 3. Standardize bullet characters to standard dash
        text = re.sub(r"[\u2022\u2023\u25E6\u2043\u2219\u25AA\u25CF]", "\n- ", text)

        # 4. Collapse runs of spaces/tabs (preserve newlines)
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]

        # 5. Remove excessive consecutive blank lines (> 2)
        cleaned_lines = []
        blank_count = 0
        for line in lines:
            if not line:
                blank_count += 1
                if blank_count <= 2:
                    cleaned_lines.append("")
            else:
                blank_count = 0
                cleaned_lines.append(line)

        clean_text = "\n".join(cleaned_lines).strip()

        # Enforce maximum character boundary to avoid resource exhaustion
        if len(clean_text) > max_chars:
            clean_text = clean_text[:max_chars]

        # 6. Extract semantic sections
        sections = cls._extract_sections(clean_text)

        words = clean_text.split()
        return NormalizedDocument(
            clean_text=clean_text,
            sections=sections,
            word_count=len(words),
            char_count=len(clean_text)
        )

    @classmethod
    def _extract_sections(cls, text: str) -> Dict[str, str]:
        """Detect section headers and split content accordingly."""
        lines = text.split("\n")
        detected_boundaries: List[tuple[int, str]] = []

        for idx, line in enumerate(lines):
            line_str = line.strip().lower()
            if not line_str or len(line_str) > 40:
                continue

            for section_name, patterns in cls.SECTION_PATTERNS.items():
                if any(re.match(pat, line_str) for pat in patterns):
                    detected_boundaries.append((idx, section_name))
                    break

        if not detected_boundaries:
            return {}

        sections: Dict[str, str] = {}
        for i, (line_idx, section_name) in enumerate(detected_boundaries):
            start = line_idx + 1
            end = detected_boundaries[i + 1][0] if i + 1 < len(detected_boundaries) else len(lines)
            section_content = "\n".join(lines[start:end]).strip()
            if section_content:
                sections[section_name] = section_content

        return sections
