from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr

class StudentDataCreate(BaseModel):
    career_goals: str

class StudentDataResponse(BaseModel):
    id: str
    user_id: str
    career_goals: str
    resume_path: Optional[str] = None
    linkedin_path: Optional[str] = None
    resume_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class CompanyDataCreate(BaseModel):
    company_name: str
    company_description: str
    website_urls: List[str] = []

class CompanyDataResponse(BaseModel):
    id: str
    user_id: str
    company_name: str
    company_description: str
    website_urls: List[str] = []
    company_data_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class JobDataCreate(BaseModel):
    job_title: str
    job_description: str
    requirements: str
    company_id: str

class JobDataResponse(BaseModel):
    id: str
    company_id: str
    job_title: str
    job_description: str
    requirements: str
    created_at: datetime
    updated_at: datetime

class AnalysisRequest(BaseModel):
    job_id: str

class AnalysisResponse(BaseModel):
    message: str
    analysis_id: str
    status: str


class UserSignup(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "student"

class UserLogin(BaseModel):
    email: EmailStr
    password: str