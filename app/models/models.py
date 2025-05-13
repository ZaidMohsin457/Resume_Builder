# app/models/models.py
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
import uuid

class SkillModel(BaseModel):
    name: str
    level: Optional[str] = None

class EducationModel(BaseModel):
    degree: Optional[str] = None
    institution: Optional[str] = None
    years: Optional[str] = None
    raw_text: Optional[str] = None

class ExperienceModel(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    date_range: Optional[str] = None
    description: Optional[str] = None

class ResumeModel(BaseModel):
    id: Optional[str] = None
    user_id: str
    full_text: Optional[str] = None
    skills: List[str] = []
    education: List[Dict[str, Any]] = []
    experience: List[Dict[str, Any]] = []
    job_titles: List[str] = []
    summary: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class JobModel(BaseModel):
    id: Optional[str] = None
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    url: Optional[HttpUrl] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    posted_date: Optional[str] = None
    employment_type: Optional[str] = None
    seniority_level: Optional[str] = None
    match_score: Optional[float] = None
    match_percentage: Optional[int] = None
    matching_skills: Optional[List[str]] = []
    missing_skills: Optional[List[str]] = []
    compatibility_note: Optional[str] = None
    created_at: Optional[datetime] = None

class JobMatchesResponse(BaseModel):
    match_id: str
    user_id: str
    resume_id: str
    matches: List[JobModel]
    created_at: datetime

class UserModel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: Optional[str] = None
    email: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

class ResumeUploadResponse(BaseModel):
    resume_id: str
    user_id: str
    message: str
    skills: List[str]
    job_titles: List[str]

class JobSearchRequest(BaseModel):
    resume_id: str
    user_id: str
    keywords: Optional[List[str]] = None
    location: Optional[str] = None
    limit: int = 20

class ErrorResponse(BaseModel):
    error: str
    details: Optional[str] = None
