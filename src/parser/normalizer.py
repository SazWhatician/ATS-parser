"""Text normalization, section segmentation, and typographic cleaning."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import re
import unicodedata


@dataclass
class NormalizedDocument:
    clean_text: str
    sections: Dict[str, str] = field(default_factory=dict)
    word_count: int = 0
    char_count: int = 0


class TextNormalizer:
    """Sanitizes raw resume text and segments it into semantic sections using 80+ fuzzy aliases and typographic heuristics."""

    # 80+ Multilingual and industry-diverse section aliases
    SECTION_PATTERNS = {
        "summary": [
            r"professional\s+summary",
            r"executive\s+summary",
            r"career\s+summary",
            r"summary\s+of\s+qualifications",
            r"profile\s+summary",
            r"career\s+objective",
            r"professional\s+profile",
            r"personal\s+statement",
            r"about\s+me",
            r"biography",
            r"overview",
            r"summary",
            r"profile",
            r"profil\s+professionnel",
            r"resumen\s+profesional"
        ],
        "experience": [
            r"work\s+experience",
            r"professional\s+experience",
            r"employment\s+history",
            r"work\s+history",
            r"career\s+history",
            r"career\s+journey",
            r"professional\s+background",
            r"relevant\s+experience",
            r"industry\s+experience",
            r"selected\s+experience",
            r"where\s+i('ve|\s+have)\s+worked",
            r"experience\s+&\s+achievements",
            r"practical\s+experience",
            r"internship\s+experience",
            r"job\s+experience",
            r"experience",
            r"exp[eé]rience\s+professionnelle",
            r"experiencia\s+laboral",
            r"berufserfahrung"
        ],
        "education": [
            r"academic\s+background",
            r"academic\s+history",
            r"education\s+&\s+credentials",
            r"educational\s+background",
            r"education\s+&\s+qualifications",
            r"degrees\s+&\s+certifications",
            r"academic\s+qualifications",
            r"university\s+education",
            r"formal\s+education",
            r"studies\s+&\s+diplomas",
            r"formation\s+acad[eé]mique",
            r"education",
            r"formation",
            r"educaci[oó]n",
            r"ausbildung"
        ],
        "skills": [
            r"technical\s+skills",
            r"core\s+competencies",
            r"skills\s+&\s+proficiencies",
            r"skills\s+&\s+abilities",
            r"skills\s+&\s+expertise",
            r"technical\s+proficiencies",
            r"areas\s+of\s+expertise",
            r"tools\s+&\s+technologies",
            r"technical\s+toolset",
            r"programming\s+languages",
            r"frameworks\s+&\s+libraries",
            r"stack\s+&\s+technologies",
            r"tech\s+stack",
            r"technologies",
            r"competencies",
            r"proficiencies",
            r"key\s+skills",
            r"skills",
            r"comp[eé]tences",
            r"habilidades",
            r"kenntnisse"
        ],
        "projects": [
            r"personal\s+projects",
            r"key\s+projects",
            r"selected\s+projects",
            r"featured\s+projects",
            r"open\s+source\s+contributions",
            r"notable\s+projects",
            r"portfolio\s+projects",
            r"academic\s+projects",
            r"technical\s+projects",
            r"what\s+i('ve|\s+have)\s+built",
            r"projects\s+&\s+contributions",
            r"projects",
            r"projets",
            r"proyectos"
        ],
        "certifications": [
            r"licenses\s+&\s+certifications",
            r"certifications\s+&\s+licenses",
            r"professional\s+certifications",
            r"certifications",
            r"certificates",
            r"accreditations",
            r"credentials",
            r"courses\s+&\s+certifications",
            r"honors\s+&\s+awards",
            r"awards\s+&\s+recognitions",
            r"certifications\s+obtenues"
        ],
    }

    @classmethod
    def normalize(cls, raw_text: str, max_chars: int = 50000) -> NormalizedDocument:
        """Clean raw resume text and extract known resume sections."""
        if not raw_text or not raw_text.strip():
            return NormalizedDocument(clean_text="", sections={}, word_count=0, char_count=0)

        # 1. Expand ligatures while maintaining precomposed unicode characters (NFC)
        text = raw_text.replace("ﬁ", "fi").replace("ﬂ", "fl").replace("ﬀ", "ff").replace("ﬃ", "ffi").replace("ﬄ", "ffl")
        text = unicodedata.normalize("NFC", text)

        # 2. Standardize non-breaking spaces, unusual spaces, and control characters
        text = text.replace("\xa0", " ").replace("\r\n", "\n").replace("\r", "\n")
        
        # 3. Standardize bullet characters to standard dash
        text = re.sub(r"[\u2022\u2023\u25E6\u2043\u2219\u25AA\u25CF\u25BA\u25B6\u27A4\u2714\u2713]", "\n- ", text)

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

        # Enforce maximum character boundary
        if len(clean_text) > max_chars:
            clean_text = clean_text[:max_chars]

        # 6. Extract semantic sections with fuzzy & typographic matching
        sections = cls._extract_sections(clean_text)

        words = clean_text.split()
        return NormalizedDocument(
            clean_text=clean_text,
            sections=sections,
            word_count=len(words),
            char_count=len(clean_text)
        )

    @classmethod
    def _clean_header_candidate(cls, line: str) -> str:
        """Strip decorative numbering, markdown, and symbols from potential header lines."""
        cleaned = re.sub(r"^[\s#*=-]*", "", line)
        cleaned = re.sub(r"[\s:*=-]*$", "", cleaned)
        cleaned = re.sub(r"^(?:\d+[\s.)|/-]+|\/\/\s*)", "", cleaned)
        cleaned = re.sub(r"[\[\]{}()]", " ", cleaned)
        return re.sub(r"\s+", " ", cleaned).strip().lower()

    @classmethod
    def _extract_sections(cls, text: str) -> Dict[str, str]:
        """Detect section headers using typographic rules and 80+ alias patterns."""
        lines = text.split("\n")
        detected_boundaries: List[Tuple[int, str, Optional[str]]] = []

        for idx, line in enumerate(lines):
            raw_line = line.strip()
            if not raw_line:
                continue

            cleaned = cls._clean_header_candidate(raw_line)
            matched_section = None
            inline_tail = None

            # 1. First check if line has inline content e.g. "Skills: Python, Go..." or "Experience: Senior..."
            for section_name, patterns in cls.SECTION_PATTERNS.items():
                for pat in patterns:
                    inline_match = re.match(rf"^[\s#*=-]*(?:{pat})[:\s|-]+(.+)$", raw_line, re.IGNORECASE)
                    if inline_match:
                        tail = inline_match.group(1).strip()
                        if tail and len(tail) > 1 and not re.match(r"^[:*=-]+$", tail):
                            matched_section = section_name
                            inline_tail = tail
                            break
                if matched_section:
                    break

            # 2. Standalone header check (lines <= 50 chars without inline tail)
            if not matched_section and cleaned and len(cleaned) <= 50:
                for section_name, patterns in cls.SECTION_PATTERNS.items():
                    for pat in patterns:
                        if re.search(rf"(?:^|\b){pat}(?:\b|$)", cleaned, re.IGNORECASE):
                            matched_section = section_name
                            break
                    if matched_section:
                        break

            if matched_section:
                detected_boundaries.append((idx, matched_section, inline_tail))

        if not detected_boundaries:
            return {}

        sections: Dict[str, str] = {}
        for i, (line_idx, section_name, inline_tail) in enumerate(detected_boundaries):
            start = line_idx + 1
            end = detected_boundaries[i + 1][0] if i + 1 < len(detected_boundaries) else len(lines)
            
            body_lines = lines[start:end]
            if inline_tail:
                body_lines = [inline_tail] + body_lines
                
            section_content = "\n".join(body_lines).strip()
            if section_content:
                if section_name in sections:
                    sections[section_name] += "\n\n" + section_content
                else:
                    sections[section_name] = section_content

        return sections
