"""Deterministic heuristic resume parser (runs 100% offline with 0 API keys)."""

import re
from typing import List, Dict, Optional, Tuple, Set, Any
from src.parser.normalizer import NormalizedDocument
from src.api.schemas.candidate import (
    CandidateProfile,
    ContactInfo,
    ExperienceItem,
    EducationItem,
    ProjectItem,
    CertificationItem,
)


class HeuristicResumeParser:
    """Offline rule- and regex-based entity extractor for resumes supporting international formats."""

    # Exhaustive dictionary of known technical skills across categories
    SKILLS_TAXONOMY = {
        "Languages": [
            "python", "javascript", "typescript", "go", "golang", "java", "c++", "c#", "rust",
            "ruby", "php", "swift", "kotlin", "scala", "r", "dart", "sql", "bash", "shell", "html", "css", "elixir", "clojure"
        ],
        "Frameworks & Libraries": [
            "fastapi", "django", "flask", "react", "react.js", "next.js", "vue", "vue.js",
            "angular", "node.js", "nodejs", "express", "express.js", "spring", "spring boot",
            "dotnet", ".net", "asp.net", "laravel", "ruby on rails", "pytorch", "tensorflow",
            "scikit-learn", "keras", "pandas", "numpy", "tailwind", "tailwindcss", "graphql",
            "langchain", "llamaindex", "huggingface", "vllm", "transformers", "polars"
        ],
        "Databases & Caching": [
            "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch",
            "sqlite", "cassandra", "dynamodb", "mariadb", "snowflake", "bigquery",
            "chromadb", "pinecone", "qdrant", "weaviate", "duckdb", "clickhouse"
        ],
        "Cloud & DevOps": [
            "docker", "kubernetes", "k8s", "aws", "amazon web services", "azure",
            "gcp", "google cloud", "terraform", "ansible", "ci/cd", "jenkins",
            "github actions", "gitlab ci", "linux", "nginx", "prometheus", "grafana",
            "helm", "argocd", "datadog"
        ],
        "Developer Tools & Practices": [
            "git", "github", "gitlab", "jira", "agile", "scrum", "rest api", "restful",
            "microservices", "grpc", "kafka", "rabbitmq", "celery", "unit testing", "tdd",
            "dbt", "airflow", "trino", "spark", "hadoop"
        ]
    }

    # Degree patterns
    DEGREE_PATTERNS = [
        r"\b(?:b\.?s\.?|b\.?sc\.?|bachelor(?:'s)?(?:\s+of\s+science)?)\b",
        r"\b(?:b\.?a\.?|bachelor(?:'s)?(?:\s+of\s+arts)?)\b",
        r"\b(?:b\.?e\.?|b\.?tech\.?|bachelor\s+of\s+engineering|bachelor\s+of\s+technology)\b",
        r"\b(?:m\.?s\.?|m\.?sc\.?|master(?:'s)?(?:\s+of\s+science)?)\b",
        r"\b(?:m\.?e\.?|m\.?tech\.?|master\s+of\s+engineering|master\s+of\s+technology)\b",
        r"\b(?:m\.?b\.?a\.?|master\s+of\s+business\s+administration)\b",
        r"\b(?:ph\.?d\.?|doctor\s+of\s+philosophy|doctorate)\b",
        r"\b(?:associate(?:'s)?\s+degree)\b",
        r"\b(?:diploma|magister|licence|licenciatura)\b",
    ]

    # Exact line matches to reject as names
    GENERIC_HEADERS_AND_TITLES = {
        "resume", "curriculum vitae", "cv", "summary", "experience", "education", "skills",
        "technical skills", "work experience", "professional experience", "projects",
        "certifications", "contact", "contact information", "personal info",
        "software engineer", "senior software engineer", "full stack developer",
        "backend developer", "frontend developer", "data scientist", "solutions architect"
    }

    @classmethod
    def parse(cls, doc: NormalizedDocument) -> CandidateProfile:
        """Extract structured candidate information from normalized resume document."""
        text = doc.clean_text
        if not text:
            return CandidateProfile(extraction_mode="heuristic")

        contact = cls._extract_contact_info(text)
        skills, categorized = cls._extract_skills(text, doc.sections.get("skills", ""))
        experience, total_exp = cls._extract_experience(text, doc.sections.get("experience", ""))
        education = cls._extract_education(text, doc.sections.get("education", ""))
        projects = cls._extract_projects(doc.sections.get("projects", ""))
        certifications = cls._extract_certifications(doc.sections.get("certifications", ""))
        summary = doc.sections.get("summary") or cls._extract_summary_fallback(text)
        domain = cls._infer_primary_domain(skills)

        return CandidateProfile(
            contact=contact,
            summary=summary,
            total_experience_years=total_exp,
            primary_domain=domain,
            skills=skills,
            categorized_skills=categorized,
            experience=experience,
            education=education,
            projects=projects,
            certifications=certifications,
            raw_text_preview=text[:300] + ("..." if len(text) > 300 else ""),
            extraction_mode="heuristic"
        )

    @classmethod
    def _extract_contact_info(cls, text: str) -> ContactInfo:
        """Extract name, email, international phone, and portfolio links."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        # 1. Name detection: first plausible line supporting Unicode, international characters, and initials
        name = None
        for line in lines[:10]:
            lower = line.lower()
            # Skip contact lines or lines with email/URLs
            if any(term in lower for term in ["@", "http:", "https:", "www.", "github.com", "linkedin.com", "phone:", "email:", "tel:"]):
                continue

            # Skip exact matches for generic resume headers or titles
            if lower in cls.GENERIC_HEADERS_AND_TITLES or lower.startswith(("curriculum vitae", "page ")):
                continue

            # Strip honorifics e.g. Dr., Prof., Mr., Ms.
            cleaned_line = re.sub(r"^(?:Dr\.|Prof\.|Mr\.|Ms\.|Mrs\.|Eng\.)\s+", "", line, flags=re.IGNORECASE).strip()
            
            # Allow accented letters (À-ÖØ-öø-ÿ), apostrophes, hyphens, and periods for initials (e.g. José Müller, Kavya N. Rao, Jane Developer)
            words = cleaned_line.split()
            if 1 <= len(words) <= 4 and re.match(r"^[A-Za-zÀ-ÖØ-öø-ÿ\s.'-]+$", cleaned_line):
                # Avoid single-word lowercase words
                if len(words) == 1 and cleaned_line.islower():
                    continue
                name = cleaned_line
                break

        # 2. Email detection
        email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text)
        email = email_match.group(0) if email_match else None

        # 3. International Phone detection
        phone = None
        # Explicit label search first
        phone_label_match = re.search(r"(?:Phone|Tel|Mobile|Cell|WhatsApp)(?:\s*Number)?[:\s]+([+0-9()\-\s.]{7,25})", text, re.IGNORECASE)
        if phone_label_match:
            phone = phone_label_match.group(1).strip()
        else:
            # Broad international regex supporting +country codes, parentheses, and spaces
            phone_match = re.search(
                r"(?:(?:\+|00)\d{1,4}[-.\s]?)?(?:\(?\d{2,5}\)?[-.\s]?)?\d{2,5}[-.\s]?\d{3,5}(?:[-.\s]?\d{1,5})?",
                text
            )
            if phone_match and len(re.sub(r"\D", "", phone_match.group(0))) >= 8:
                phone = phone_match.group(0).strip()

        # 4. Social & Portfolio Links
        linkedin_match = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9_-]+", text, re.IGNORECASE)
        linkedin = linkedin_match.group(0) if linkedin_match else None

        github_match = re.search(r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_-]+", text, re.IGNORECASE)
        github = github_match.group(0) if github_match else None

        # 5. Location detection
        location = None
        loc_match = re.search(r"(?:Location|Address|City):\s*([^\n|]+)", text, re.IGNORECASE)
        if loc_match:
            location = loc_match.group(1).strip()
        else:
            for line in lines[:8]:
                # City, State or City, Country format
                city_match = re.search(r"\b([A-Z][a-zA-Z\s]+,\s*(?:[A-Z]{2}(?:\s+\d{5})?|[A-Z][a-zA-Z\s]+))\b", line)
                if city_match and not any(term in line.lower() for term in ["university", "company", "school"]):
                    location = city_match.group(1).strip()
                    break

        return ContactInfo(
            name=name,
            email=email,
            phone=phone,
            location=location,
            linkedin=linkedin,
            github=github,
        )

    # --- Skills Extraction ---

    @classmethod
    def _extract_skills(cls, full_text: str, skills_section: str) -> Tuple[List[str], Dict[str, List[str]]]:
        """Extract and categorize skills against technical taxonomy."""
        target_text = f"{skills_section}\n{full_text}".lower()
        extracted_skills: List[str] = []
        categorized: Dict[str, List[str]] = {}

        for category, skill_list in cls.SKILLS_TAXONOMY.items():
            cat_matches: List[str] = []
            for skill in skill_list:
                escaped = re.escape(skill)
                pattern = rf"(?<![\w#+.]){escaped}(?![\w#+])"
                if re.search(pattern, target_text):
                    display_name = cls._format_skill_casing(skill)
                    cat_matches.append(display_name)
                    if display_name not in extracted_skills:
                        extracted_skills.append(display_name)
            if cat_matches:
                categorized[category] = sorted(cat_matches)

        return sorted(extracted_skills), categorized

    @staticmethod
    def _format_skill_casing(skill: str) -> str:
        """Preserve standard casing for tech skills."""
        custom_casing = {
            "fastapi": "FastAPI",
            "javascript": "JavaScript",
            "typescript": "TypeScript",
            "postgresql": "PostgreSQL",
            "mongodb": "MongoDB",
            "sqlite": "SQLite",
            "graphql": "GraphQL",
            "github": "GitHub",
            "gitlab": "GitLab",
            "next.js": "Next.js",
            "vue.js": "Vue.js",
            "react.js": "React.js",
            "node.js": "Node.js",
            "express.js": "Express.js",
            "aws": "AWS",
            "gcp": "GCP",
            "rest api": "REST APIs",
            "microservices": "Microservices",
            "ci/cd": "CI/CD",
            "tdd": "TDD",
            "c++": "C++",
            "c#": "C#",
            "html": "HTML",
            "css": "CSS",
            "sql": "SQL",
            "r": "R",
            "langchain": "LangChain",
            "llamaindex": "LlamaIndex",
            "chromadb": "ChromaDB",
            "duckdb": "DuckDB"
        }
        return custom_casing.get(skill.lower(), skill.title())

    # --- Experience Extraction with Adaptive Dates ---

    @classmethod
    def _extract_experience(cls, full_text: str, exp_section: str) -> Tuple[List[ExperienceItem], Optional[float]]:
        """Parse employment history supporting international month names, quarters, and dotted dates."""
        target_text = exp_section if exp_section else full_text
        lines = [line.strip() for line in target_text.split("\n") if line.strip()]

        experiences: List[ExperienceItem] = []
        # Multi-format date regex
        date_pattern = (
            r"(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
            r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|"
            r"Q[1-4]|\d{1,2})[\s,./-]+)?\b(19\d{2}|20\d{2})\b"
            r"\s*(?:-|–|—|to|until|till)\s*"
            r"(?:(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
            r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|"
            r"Q[1-4]|\d{1,2})[\s,./-]+)?\b(19\d{2}|20\d{2})\b|Present|Current|Now|Ongoing)"
        )

        current_exp: Optional[Dict[str, Any]] = None
        years_found: List[int] = []

        for line in lines:
            match = re.search(date_pattern, line, re.IGNORECASE)
            if match:
                if current_exp:
                    experiences.append(ExperienceItem(**current_exp))

                # Extract start and end year
                all_years = [int(y) for y in re.findall(r"\b(19\d{2}|20\d{2})\b", match.group(0))]
                start_yr = all_years[0] if all_years else 2020
                end_yr = all_years[1] if len(all_years) > 1 else 2026
                years_found.extend([start_yr, end_yr])

                end_str = "Present" if any(w in match.group(0).lower() for w in ["present", "current", "now", "ongoing"]) else str(end_yr)

                # Parse company and role from header
                header_part = line[:match.start()].strip(" |-–—,\t")
                if not header_part:
                    # Look at next part
                    header_part = line[match.end():].strip(" |-–—,\t")

                company = "Company"
                role = "Professional Role"

                if "|" in header_part:
                    parts = [p.strip() for p in header_part.split("|") if p.strip()]
                    role = parts[0] if parts else role
                    company = parts[1] if len(parts) > 1 else company
                elif " at " in header_part:
                    parts = header_part.split(" at ")
                    role = parts[0].strip()
                    company = parts[1].strip()
                elif " - " in header_part:
                    parts = header_part.split(" - ")
                    role = parts[0].strip()
                    company = parts[1].strip()
                elif header_part:
                    role = header_part

                current_exp = {
                    "company": company,
                    "role": role,
                    "start_date": str(start_yr),
                    "end_date": end_str,
                    "duration": f"{max(1, end_yr - start_yr)} years",
                    "highlights": [],
                    "technologies": []
                }
            elif current_exp:
                # Capture bullet points
                if line.startswith(("-", "*", "•", "–")):
                    clean_highlight = line.lstrip("-*•– \t")
                    if clean_highlight:
                        current_exp["highlights"].append(clean_highlight)

        if current_exp:
            experiences.append(ExperienceItem(**current_exp))

        # Calculate estimated total experience years
        total_exp_years = None
        if years_found:
            min_yr = min(years_found)
            max_yr = max(years_found)
            total_exp_years = float(max(1, max_yr - min_yr))

        return experiences, total_exp_years

    # --- Education Extraction ---

    @classmethod
    def _extract_education(cls, full_text: str, edu_section: str) -> List[EducationItem]:
        """Extract academic degrees, institutions, and graduation dates."""
        target_text = edu_section if edu_section else full_text
        lines = [line.strip() for line in target_text.split("\n") if line.strip()]

        education_items: List[EducationItem] = []
        uni_keywords = ["university", "college", "institute", "school", "academy", "polytechnic", "universidad", "université"]

        for line in lines:
            lower = line.lower()
            is_uni = any(kw in lower for kw in uni_keywords)
            has_degree = any(re.search(pat, lower) for pat in cls.DEGREE_PATTERNS)

            if is_uni or has_degree:
                year_match = re.search(r"\b(19\d{2}|20\d{2})\b", line)
                grad_year = year_match.group(0) if year_match else None

                institution = line
                degree = None

                if "|" in line:
                    parts = [p.strip() for p in line.split("|") if p.strip()]
                    if len(parts) >= 2:
                        p0, p1 = parts[0], parts[1]
                        p0_uni = any(kw in p0.lower() for kw in uni_keywords)
                        p1_uni = any(kw in p1.lower() for kw in uni_keywords)
                        if p1_uni and not p0_uni:
                            institution = p1
                            degree = p0
                        else:
                            institution = p0
                            degree = p1
                elif " - " in line:
                    parts = [p.strip() for p in line.split(" - ") if p.strip()]
                    if len(parts) >= 2:
                        institution = parts[0]
                        degree = parts[1]

                for pat in cls.DEGREE_PATTERNS:
                    match = re.search(pat, line, re.IGNORECASE)
                    if match:
                        degree = match.group(0).title()
                        break

                education_items.append(EducationItem(
                    institution=institution,
                    degree=degree or "Degree / Certificate",
                    field_of_study=None,
                    graduation_year=grad_year
                ))

        return education_items

    # --- Projects & Certifications ---

    @classmethod
    def _extract_projects(cls, projects_section: str) -> List[ProjectItem]:
        if not projects_section:
            return []
        items = []
        for line in projects_section.split("\n"):
            line = line.strip()
            if line and len(line) > 5 and not line.startswith(("-", "*", "•")):
                items.append(ProjectItem(name=line[:50], description=line, technologies=[]))
        return items[:5]

    @classmethod
    def _extract_certifications(cls, cert_section: str) -> List[CertificationItem]:
        if not cert_section:
            return []
        certs = []
        for line in cert_section.split("\n"):
            line = line.strip().lstrip("-*• \t")
            if line and 4 <= len(line) <= 80:
                certs.append(CertificationItem(name=line))
        return certs[:6]

    @classmethod
    def _extract_summary_fallback(cls, text: str) -> Optional[str]:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines[1:6]:
            if len(line.split()) >= 15 and not line.startswith(("-", "*", "•")):
                return line
        return None

    @classmethod
    def _infer_primary_domain(cls, skills: List[str]) -> str:
        s_lower = {s.lower() for s in skills}
        if any(s in s_lower for s in ["fastapi", "django", "go", "golang", "postgresql", "microservices"]):
            return "Backend Engineering"
        elif any(s in s_lower for s in ["react", "next.js", "vue", "javascript", "typescript", "tailwind"]):
            return "Frontend Engineering"
        elif any(s in s_lower for s in ["pytorch", "tensorflow", "scikit-learn", "pandas", "langchain"]):
            return "Machine Learning & AI"
        elif any(s in s_lower for s in ["kubernetes", "docker", "terraform", "aws", "gcp"]):
            return "DevOps & Cloud"
        return "Software Engineering"
