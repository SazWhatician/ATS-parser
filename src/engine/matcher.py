"""ATS Job Matching and Rubric-Based Scoring Engine."""

import re
from typing import Dict, List, Set, Tuple, Optional
from src.api.schemas.candidate import CandidateProfile
from src.api.schemas.matching import ATSScoreReport, ScoreCategory
from src.engine.heuristics import HeuristicResumeParser


class ATSMatcher:
    """Evaluates candidate profiles against target job descriptions using a 4-tier rubric."""

    WEIGHT_SKILLS = 0.40
    WEIGHT_EXPERIENCE = 0.35
    WEIGHT_EDUCATION = 0.15
    WEIGHT_QUALITY = 0.10

    def evaluate(self, candidate: CandidateProfile, job_description: str) -> ATSScoreReport:
        """Evaluate candidate profile against target job description."""
        clean_jd = (job_description or "").strip()
        if not clean_jd:
            return ATSScoreReport(
                overall_score=50.0,
                match_level="Neutral",
                recommendation="No job description provided for comparison. Displaying candidate profile only.",
                categories={
                    "technical_skills": ScoreCategory(
                        score=50.0,
                        weight=self.WEIGHT_SKILLS,
                        reasoning="Job description not provided."
                    ),
                    "experience": ScoreCategory(
                        score=50.0,
                        weight=self.WEIGHT_EXPERIENCE,
                        reasoning="Job description not provided."
                    ),
                    "education": ScoreCategory(
                        score=50.0,
                        weight=self.WEIGHT_EDUCATION,
                        reasoning="Job description not provided."
                    ),
                    "quality": ScoreCategory(
                        score=50.0,
                        weight=self.WEIGHT_QUALITY,
                        reasoning="Job description not provided."
                    ),
                },
                strengths=["Candidate profile successfully extracted."],
                gaps=["Target job requirements not supplied."],
                matched_skills=[],
                missing_skills=[]
            )

        # 1. Technical Skills Evaluation
        skills_cat, matched_skills, missing_skills = self._evaluate_skills(candidate, clean_jd)

        # 2. Experience Evaluation
        exp_cat = self._evaluate_experience(candidate, clean_jd)

        # 3. Education Evaluation
        edu_cat = self._evaluate_education(candidate, clean_jd)

        # 4. Profile Quality & Completeness Evaluation
        qual_cat = self._evaluate_quality(candidate)

        # Weighted calculation
        overall = (
            (skills_cat.score * self.WEIGHT_SKILLS) +
            (exp_cat.score * self.WEIGHT_EXPERIENCE) +
            (edu_cat.score * self.WEIGHT_EDUCATION) +
            (qual_cat.score * self.WEIGHT_QUALITY)
        )
        overall_score = round(min(100.0, max(0.0, overall)), 1)

        # Match level
        if overall_score >= 75.0:
            match_level = "Strong Match"
        elif overall_score >= 50.0:
            match_level = "Potential Match"
        else:
            match_level = "Weak Match"

        # Synthesis: Strengths & Gaps
        strengths, gaps = self._synthesize_strengths_and_gaps(
            candidate, skills_cat, exp_cat, edu_cat, matched_skills, missing_skills
        )

        recommendation = self._generate_recommendation(match_level, overall_score, candidate, matched_skills, missing_skills)

        return ATSScoreReport(
            overall_score=overall_score,
            match_level=match_level,
            recommendation=recommendation,
            categories={
                "technical_skills": skills_cat,
                "experience": exp_cat,
                "education": edu_cat,
                "quality": qual_cat,
            },
            strengths=strengths,
            gaps=gaps,
            matched_skills=matched_skills,
            missing_skills=missing_skills
        )

    # --- Sub-Evaluations ---

    def _evaluate_skills(
        self, candidate: CandidateProfile, jd_text: str
    ) -> Tuple[ScoreCategory, List[str], List[str]]:
        """Extract skills mentioned in JD and compare against candidate skills."""
        candidate_skills_lower = {s.lower(): s for s in candidate.skills}
        
        # Detect skills in JD using our taxonomy
        jd_skills: Set[str] = set()
        for cat_skills in HeuristicResumeParser.SKILLS_TAXONOMY.values():
            for skill in cat_skills:
                escaped = re.escape(skill)
                pattern = rf"(?<![\w#+]){escaped}(?![\w#+])"
                if re.search(pattern, jd_text, re.IGNORECASE):
                    jd_skills.add(skill.lower())

        if not jd_skills:
            # If JD has no standard tech keywords, give default high baseline if candidate has skills
            score = 75.0 if candidate.skills else 40.0
            return (
                ScoreCategory(
                    score=score,
                    weight=self.WEIGHT_SKILLS,
                    reasoning="Few specific technical keywords identified in job description.",
                    matches=candidate.skills[:5],
                    missing=[]
                ),
                candidate.skills[:5],
                []
            )

        matched_lower = jd_skills.intersection(candidate_skills_lower.keys())
        missing_lower = jd_skills.difference(candidate_skills_lower.keys())

        matched_skills = [
            candidate_skills_lower[k] for k in matched_lower
        ]
        missing_skills = [
            HeuristicResumeParser._format_skill_casing(k) for k in missing_lower
        ]

        match_ratio = len(matched_lower) / len(jd_skills)
        # Scale to 0-100 score
        raw_score = match_ratio * 100.0
        # If candidate has extra skills in same domain, award up to 10 bonus points
        bonus = min(10.0, len(candidate.skills) * 0.5)
        final_score = min(100.0, raw_score + bonus)

        reasoning = (
            f"Candidate matches {len(matched_lower)} of {len(jd_skills)} required technical skills "
            f"({match_ratio:.0%})."
        )

        return (
            ScoreCategory(
                score=round(final_score, 1),
                weight=self.WEIGHT_SKILLS,
                reasoning=reasoning,
                matches=matched_skills,
                missing=missing_skills
            ),
            matched_skills,
            missing_skills
        )

    def _evaluate_experience(self, candidate: CandidateProfile, jd_text: str) -> ScoreCategory:
        """Compare candidate experience against JD requirements."""
        # Find required years in JD
        req_match = re.search(r"(\d+)\+?\s*(?:years|yrs)", jd_text, re.IGNORECASE)
        required_years = float(req_match.group(1)) if req_match else 3.0

        cand_years = candidate.total_experience_years or 0.0
        
        # Calculate ratio
        if cand_years >= required_years:
            score = 90.0 + min(10.0, (cand_years - required_years) * 2)
            reasoning = f"Candidate has {cand_years:.1f} years of experience, exceeding the required {required_years:.0f} years."
        elif cand_years > 0:
            ratio = cand_years / required_years
            score = ratio * 85.0
            reasoning = f"Candidate has {cand_years:.1f} years vs. {required_years:.0f} required years ({ratio:.0%} match)."
        else:
            score = 50.0
            reasoning = "Experience duration could not be accurately calculated from resume dates."

        # Check job title relevance
        title_match = re.search(r"(?:Job Title|Role|Position):\s*([^\n]+)", jd_text, re.IGNORECASE)
        target_title = title_match.group(1).strip() if title_match else ""
        if target_title:
            matches = [exp.role for exp in candidate.experience if any(w.lower() in exp.role.lower() for w in target_title.split())]
        else:
            matches = [exp.role for exp in candidate.experience[:2]]

        return ScoreCategory(
            score=round(min(100.0, max(0.0, score)), 1),
            weight=self.WEIGHT_EXPERIENCE,
            reasoning=reasoning,
            matches=matches,
            missing=[] if cand_years >= required_years else [f"{required_years - cand_years:.1f} more years required"]
        )

    def _evaluate_education(self, candidate: CandidateProfile, jd_text: str) -> ScoreCategory:
        """Evaluate educational degrees against job requirements."""
        jd_lower = jd_text.lower()
        requires_phd = "ph.d" in jd_lower or "doctorate" in jd_lower
        requires_master = "master" in jd_lower or "m.s." in jd_lower or "mba" in jd_lower
        requires_bachelor = "bachelor" in jd_lower or "b.s." in jd_lower or "degree" in jd_lower

        cand_degrees = " ".join([f"{e.degree or ''} {e.institution}" for e in candidate.education]).lower()
        cand_has_phd = any(p in cand_degrees for p in ["ph.d", "doctorate"])
        cand_has_master = any(p in cand_degrees for p in ["master", "m.s", "m.tech", "mba"])
        cand_has_bachelor = any(p in cand_degrees for p in ["bachelor", "b.s", "b.tech", "b.e", "degree"])

        score = 80.0
        reasoning = "Educational qualifications meet baseline requirements."

        if requires_phd:
            if cand_has_phd:
                score = 100.0
                reasoning = "Candidate holds required doctoral degree."
            elif cand_has_master:
                score = 75.0
                reasoning = "Candidate holds Master's degree (Ph.D. preferred)."
            else:
                score = 60.0
                reasoning = "Candidate lacks required doctoral degree."
        elif requires_master:
            if cand_has_phd or cand_has_master:
                score = 100.0
                reasoning = "Candidate holds required advanced degree."
            elif cand_has_bachelor:
                score = 80.0
                reasoning = "Candidate holds Bachelor's degree (Master's preferred)."
            else:
                score = 65.0
                reasoning = "Advanced degree not explicitly stated."
        else:
            if cand_has_phd or cand_has_master or cand_has_bachelor:
                score = 95.0
                reasoning = "Candidate possesses relevant higher education credentials."
            elif candidate.education:
                score = 85.0
                reasoning = "Candidate possesses educational background."
            else:
                score = 70.0
                reasoning = "No formal degree detected in resume."

        matches = [f"{e.degree} from {e.institution}" if e.degree else e.institution for e in candidate.education]
        return ScoreCategory(
            score=round(score, 1),
            weight=self.WEIGHT_EDUCATION,
            reasoning=reasoning,
            matches=matches,
            missing=[] if score >= 80 else ["Higher degree preferred"]
        )

    def _evaluate_quality(self, candidate: CandidateProfile) -> ScoreCategory:
        """Check resume completeness, structure, and professional presentation."""
        score = 70.0
        reasons = []

        # Check contact completeness
        if candidate.contact.email and candidate.contact.phone:
            score += 10.0
            reasons.append("Complete contact info")
        if candidate.contact.github or candidate.contact.linkedin:
            score += 10.0
            reasons.append("Professional profile links provided")

        # Check bullet points / highlights in experience
        has_highlights = any(len(exp.highlights) > 0 for exp in candidate.experience)
        if has_highlights:
            score += 10.0
            reasons.append("Structured accomplishment highlights present")

        return ScoreCategory(
            score=round(min(100.0, score), 1),
            weight=self.WEIGHT_QUALITY,
            reasoning=", ".join(reasons) if reasons else "Standard resume structure.",
            matches=reasons,
            missing=[]
        )

    # --- Synthesis Helpers ---

    def _synthesize_strengths_and_gaps(
        self,
        candidate: CandidateProfile,
        skills_cat: ScoreCategory,
        exp_cat: ScoreCategory,
        edu_cat: ScoreCategory,
        matched_skills: List[str],
        missing_skills: List[str]
    ) -> Tuple[List[str], List[str]]:
        strengths: List[str] = []
        gaps: List[str] = []

        if len(matched_skills) >= 3:
            strengths.append(f"Strong match on core tech stack: {', '.join(matched_skills[:4])}.")
        if candidate.total_experience_years and candidate.total_experience_years >= 4.0:
            strengths.append(f"Solid career experience ({candidate.total_experience_years:.0f}+ years) in {candidate.primary_domain or 'engineering'}.")
        if edu_cat.score >= 90.0 and candidate.education:
            strengths.append(f"Verified academic degree: {candidate.education[0].institution}.")

        if missing_skills:
            gaps.append(f"Missing mentions of key technologies: {', '.join(missing_skills[:4])}.")
        if exp_cat.score < 70.0:
            gaps.append("Years of experience may be below target requirements.")
        if not candidate.contact.linkedin and not candidate.contact.github:
            gaps.append("No LinkedIn or GitHub profile links provided for verification.")

        if not strengths:
            strengths.append("Candidate demonstrates baseline professional competencies.")
        if not gaps:
            gaps.append("No critical qualification gaps identified.")

        return strengths, gaps

    def _generate_recommendation(
        self,
        match_level: str,
        overall_score: float,
        candidate: CandidateProfile,
        matched_skills: List[str],
        missing_skills: List[str]
    ) -> str:
        name = candidate.contact.name or "The candidate"
        if match_level == "Strong Match":
            return (
                f"{name} is a high-confidence match ({overall_score:.1f}%) for this role. "
                f"Possesses strong alignment with core requirements ({', '.join(matched_skills[:3])}). "
                "Recommended to advance immediately to technical interview."
            )
        elif match_level == "Potential Match":
            missing_text = f", though lacks explicit mention of {', '.join(missing_skills[:2])}" if missing_skills else ""
            return (
                f"{name} is a potential candidate ({overall_score:.1f}%){missing_text}. "
                "Recommended for an initial recruiter screening call to clarify experience depth."
            )
        else:
            return (
                f"{name} has significant skill or experience gaps for this specific position ({overall_score:.1f}%). "
                "Recommend reviewing alternative roles or junior positions."
            )
