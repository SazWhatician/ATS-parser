"""Deterministic heuristic resume parser (runs 100% offline with 0 API keys)."""

import re
from typing import List, Dict, Optional, Tuple, Set
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
    """Offline rule- and regex-based entity extractor for resumes."""

    # Exhaustive dictionary of known technical skills across categories
    SKILLS_TAXONOMY = {
        "Languages": [
            "python", "javascript", "typescript", "go", "golang", "java", "c++", "c#", "rust",
            "ruby", "php", "swift", "kotlin", "scala", "r", "dart", "sql", "bash", "shell", "html", "css"
        ],
        "Frameworks & Libraries": [
            "fastapi", "django", "flask", "react", "react.js", "next.js", "vue", "vue.js",
            "angular", "node.js", "nodejs", "express", "express.js", "spring", "spring boot",
            "dotnet", ".net", "asp.net", "laravel", "ruby on rails", "pytorch", "tensorflow",
            "scikit-learn", "keras", "pandas", "numpy", "tailwind", "tailwindcss", "graphql"
        ],
        "Databases & Caching": [
            "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch",
            "sqlite", "cassandra", "dynamodb", "mariadb", "snowflake", "bigquery"
        ],
        "Cloud & DevOps": [
            "docker", "kubernetes", "k8s", "aws", "amazon web services", "azure",
            "gcp", "google cloud", "terraform", "ansible", "ci/cd", "jenkins",
            "github actions", "gitlab ci", "linux", "nginx", "prometheus", "grafana"
        ],
        "Developer Tools & Practices": [
            "git", "github", "gitlab", "jira", "agile", "scrum", "rest api", "restful",
            "microservices", "grpc", "kafka", "rabbitmq", "celery", "unit testing", "tdd"
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
    ]

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

    # --- Contact Info Extraction ---

    @classmethod
    def _extract_contact_info(cls, text: str) -> ContactInfo:
        """Extract name, email, phone, and links."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        # 1. Name detection: first plausible line before contact symbols
        name = None
        for line in lines[:6]:
            lower = line.lower()
            if any(term in lower for term in ["resume", "curriculum vitae", "cv", "page", "email:", "phone:"]):
                continue
            # If line is 2-4 words and contains letters only
            words = line.split()
            if 1 <= len(words) <= 4 and re.match(r"^[A-Za-z\s.'-]+$", line):
                name = line.strip()
                break

        # 2. Email detection
        email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text)
        email = email_match.group(0) if email_match else None

        # 3. Phone detection
        phone = None
        phone_label_match = re.search(r"(?:Phone|Tel|Mobile|Cell)(?:\s*Number)?[:\s]+([+0-9()\-\s.]{7,25})", text, re.IGNORECASE)
        if phone_label_match:
            phone = phone_label_match.group(1).strip()
        else:
            phone_match = re.search(
                r"(?:(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\+?\d{10,14})",
                text
            )
            phone = phone_match.group(0).strip() if phone_match else None

        # 4. Social & Portfolio Links
        linkedin_match = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9_-]+", text, re.IGNORECASE)
        linkedin = linkedin_match.group(0) if linkedin_match else None

        github_match = re.search(r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_-]+", text, re.IGNORECASE)
        github = github_match.group(0) if github_match else None

        # 5. Location detection
        location = None
        loc_match = re.search(r"(?:Location|Address):\s*([^\n|]+)", text, re.IGNORECASE)
        if loc_match:
            location = loc_match.group(1).strip()
        else:
            # Check for "City, State" pattern in the top 5 lines
            for line in lines[:6]:
                city_match = re.search(r"\b([A-Z][a-zA-Z\s]+,\s*[A-Z]{2}(?:\s+\d{5})?)\b", line)
                if city_match:
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
                # Use word boundary matching
                escaped = re.escape(skill)
                # Ensure special characters like ++ or . are handled in regex
                pattern = rf"(?<![\w#+]){escaped}(?![\w#+])"
                if re.search(pattern, target_text):
                    # Proper display casing
                    display_name = cls._format_skill_casing(skill)
                    cat_matches.append(display_name)
                    if display_name not in extracted_skills:
                        extracted_skills.append(display_name)
            if cat_matches:
                categorized[category] = sorted(cat_matches)

        return sorted(extracted_skills), categorized

    @classmethod
    def _format_skill_casing(cls, skill: str) -> str:
        """Convert lowercase skill keys to canonical industry casing."""
        casing_map = {
            "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript",
            "go": "Go", "golang": "Go", "java": "Java", "c++": "C++", "c#": "C#",
            "rust": "Rust", "ruby": "Ruby", "php": "PHP", "swift": "Swift", "kotlin": "Kotlin",
            "sql": "SQL", "html": "HTML", "css": "CSS", "fastapi": "FastAPI",
            "django": "Django", "flask": "Flask", "react": "React", "react.js": "React",
            "next.js": "Next.js", "vue": "Vue.js", "vue.js": "Vue.js", "node.js": "Node.js",
            "nodejs": "Node.js", "express": "Express.js", "spring": "Spring",
            "spring boot": "Spring Boot", "docker": "Docker", "kubernetes": "Kubernetes",
            "k8s": "Kubernetes", "aws": "AWS", "gcp": "GCP", "azure": "Azure",
            "postgresql": "PostgreSQL", "postgres": "PostgreSQL", "mysql": "MySQL",
            "mongodb": "MongoDB", "redis": "Redis", "elasticsearch": "Elasticsearch",
            "graphql": "GraphQL", "git": "Git", "github": "GitHub", "rest api": "REST API"
        }
        return casing_map.get(skill, skill.title())

    # --- Work Experience Extraction ---

    @classmethod
    def _extract_experience(cls, full_text: str, exp_section: str) -> Tuple[List[ExperienceItem], Optional[float]]:
        """Parse employment history and calculate total experience."""
        target_text = exp_section if exp_section else full_text
        lines = [line.strip() for line in target_text.split("\n") if line.strip()]

        experiences: List[ExperienceItem] = []
        date_pattern = r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?\b(19\d{2}|20\d{2})\b\s*(?:-|–|—|to)\s*(?:(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+)?\b(19\d{2}|20\d{2})\b|Present|Current)"

        current_exp: Optional[Dict[str, Any]] = None
        years_found: List[int] = []

        for line in lines:
            match = re.search(date_pattern, line, re.IGNORECASE)
            if match:
                # Save previous experience item
                if current_exp:
                    experiences.append(ExperienceItem(**current_exp))

                start_yr = int(match.group(1))
                end_str = match.group(2)
                end_yr = int(end_str) if end_str else 2026
                years_found.append(start_yr)
                years_found.append(end_yr)

                # Parse company and role from preceding or current line
                header_part = line[:match.start()].strip(" |-–—,\t")
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
                elif header_part:
                    role = header_part

                current_exp = {
                    "company": company,
                    "role": role,
                    "start_date": str(start_yr),
                    "end_date": end_str or "Present",
                    "duration": f"{max(1, end_yr - start_yr)} years",
                    "highlights": [],
                    "technologies": []
                }
            elif current_exp:
                # Add highlights
                if line.startswith(("-", "*", "•")):
                    clean_highlight = line.lstrip("-*• \t")
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
        uni_keywords = ["university", "college", "institute", "school", "academy", "polytechnic"]

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
                    elif parts:
                        institution = parts[0]
                elif " - " in line:
                    parts = [p.strip() for p in line.split(" - ") if p.strip()]
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
                    elif parts:
                        institution = parts[0]

                education_items.append(EducationItem(
                    institution=institution,
                    degree=degree,
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
            if line and len(line) > 5 and not line.startswith(("-", "*")):
                items.append(ProjectItem(name=line[:50], description=line))
        return items[:5]

    @classmethod
    def _extract_certifications(cls, cert_section: str) -> List[CertificationItem]:
        if not cert_section:
            return []
        certs = []
        for line in cert_section.split("\n"):
            line = line.strip(" -*•")
            if line and len(line) > 3:
                certs.append(CertificationItem(name=line))
        return certs[:6]

    @classmethod
    def _extract_summary_fallback(cls, text: str) -> Optional[str]:
        """Fallback summary from top paragraphs if no explicit section header exists."""
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip().split()) > 15]
        return paragraphs[0] if paragraphs else None

    @classmethod
    def _infer_primary_domain(cls, skills: List[str]) -> str:
        """Infer high-level domain from extracted skill frequencies."""
        skills_lower = [s.lower() for s in skills]
        backend_score = sum(1 for s in ["python", "go", "fastapi", "django", "sql", "postgresql", "docker"] if s in skills_lower)
        frontend_score = sum(1 for s in ["javascript", "typescript", "react", "vue", "html", "css", "tailwind"] if s in skills_lower)
        ml_score = sum(1 for s in ["pytorch", "tensorflow", "scikit-learn", "pandas", "numpy"] if s in skills_lower)
        devops_score = sum(1 for s in ["kubernetes", "terraform", "aws", "gcp", "docker", "ci/cd"] if s in skills_lower)

        scores = {
            "Backend Engineering": backend_score,
            "Frontend / Web": frontend_score,
            "AI / Machine Learning": ml_score,
            "DevOps / Cloud Platform": devops_score
        }
        top_domain = max(scores, key=scores.get)
        return top_domain if scores[top_domain] > 0 else "Software Engineering"
