"""Pydantic models representing extracted candidate profile data."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class ContactInfo(BaseModel):
    name: Optional[str] = Field(None, description="Candidate full name")
    email: Optional[str] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    location: Optional[str] = Field(None, description="City, State / Country")
    linkedin: Optional[str] = Field(None, description="LinkedIn profile URL")
    github: Optional[str] = Field(None, description="GitHub profile URL")
    portfolio: Optional[str] = Field(None, description="Personal website or portfolio URL")


class ExperienceItem(BaseModel):
    company: str = Field(..., description="Company or organization name")
    role: str = Field(..., description="Job title / position")
    location: Optional[str] = Field(None, description="Job location")
    duration: Optional[str] = Field(None, description="Calculated duration (e.g. 2 years 4 months)")
    start_date: Optional[str] = Field(None, description="Start date (YYYY or Month YYYY)")
    end_date: Optional[str] = Field(None, description="End date or 'Present'")
    highlights: List[str] = Field(default_factory=list, description="Key accomplishments or bullet points")
    technologies: List[str] = Field(default_factory=list, description="Technologies or tools used")


class EducationItem(BaseModel):
    institution: str = Field(..., description="University, college, or school")
    degree: Optional[str] = Field(None, description="Degree or qualification (e.g. B.S., M.S., Ph.D.)")
    field_of_study: Optional[str] = Field(None, description="Major / field of study")
    graduation_year: Optional[str] = Field(None, description="Graduation year or date range")
    grade: Optional[str] = Field(None, description="GPA or grade / honors")


class ProjectItem(BaseModel):
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project summary")
    url: Optional[str] = Field(None, description="Repository or live URL")
    technologies: List[str] = Field(default_factory=list, description="Technologies utilized")


class CertificationItem(BaseModel):
    name: str = Field(..., description="Certification name")
    issuer: Optional[str] = Field(None, description="Issuing organization (e.g. AWS, Google, Cisco)")
    year: Optional[str] = Field(None, description="Year earned or valid through")


class CandidateProfile(BaseModel):
    contact: ContactInfo = Field(default_factory=ContactInfo)
    summary: Optional[str] = Field(None, description="Professional summary or objective")
    total_experience_years: Optional[float] = Field(None, description="Estimated total experience in years")
    primary_domain: Optional[str] = Field(None, description="Primary domain (e.g. Backend, Frontend, ML/AI)")
    skills: List[str] = Field(default_factory=list, description="Deduplicated list of technical and domain skills")
    categorized_skills: Dict[str, List[str]] = Field(default_factory=dict, description="Skills grouped by category")
    experience: List[ExperienceItem] = Field(default_factory=list, description="Chronological work history")
    education: List[EducationItem] = Field(default_factory=list, description="Academic background")
    projects: List[ProjectItem] = Field(default_factory=list, description="Notable projects")
    certifications: List[CertificationItem] = Field(default_factory=list, description="Licenses and certifications")
    raw_text_preview: Optional[str] = Field(None, description="Brief preview of raw parsed text")
    extraction_mode: str = Field("heuristic", description="'heuristic' or 'llm'")
