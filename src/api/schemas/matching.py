"""Pydantic models representing ATS scoring and job matching reports."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from src.api.schemas.candidate import CandidateProfile


class ScoreCategory(BaseModel):
    score: float = Field(..., ge=0.0, le=100.0, description="Category score out of 100")
    weight: float = Field(..., ge=0.0, le=1.0, description="Weight factor in overall calculation")
    reasoning: str = Field(..., description="Explanation of evaluation and deductions")
    matches: List[str] = Field(default_factory=list, description="Specific matched items")
    missing: List[str] = Field(default_factory=list, description="Specific missing requirements")


class ATSScoreReport(BaseModel):
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Final weighted ATS match score (0-100)")
    match_level: str = Field(..., description="E.g., 'Strong Match', 'Potential Match', 'Weak Match'")
    recommendation: str = Field(default="Candidate shows strong overall qualifications.", description="Recruiter summary recommendation")
    categories: Dict[str, ScoreCategory] = Field(
        default_factory=dict,
        description="Detailed category scores: technical_skills, experience, education, quality"
    )
    strengths: List[str] = Field(default_factory=list, description="Top positive candidate alignments")
    gaps: List[str] = Field(default_factory=list, description="Critical missing skills or deficiencies")
    matched_skills: List[str] = Field(default_factory=list, description="Skills found in both resume and JD")
    missing_skills: List[str] = Field(default_factory=list, description="Required skills absent from resume")


class CandidateEvaluationResponse(BaseModel):
    profile: CandidateProfile = Field(..., description="Extracted candidate details")
    score_report: Optional[ATSScoreReport] = Field(None, description="ATS evaluation report against job description")
    processing_time_ms: float = Field(..., description="Total processing time in milliseconds")
    engine_mode: str = Field(..., description="'heuristic' or 'llm'")
