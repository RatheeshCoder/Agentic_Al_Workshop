from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Depends
from typing import Optional
from app.utils.auth_utils import get_current_user
from app.models.user_model import StudentDataResponse, CompanyDataResponse, JobDataCreate, JobDataResponse, AnalysisRequest, AnalysisResponse
from app.services.user import (
    handle_create_student_data,
    handle_create_company_data,
    handle_create_job_data,
    handle_analyze_compatibility,
    handle_get_student_data,
    handle_get_company_data,
    handle_get_company_jobs
)

router = APIRouter()

@router.post("/student-data", response_model=StudentDataResponse)
async def create_student_data(
    career_goals: str = Form(...),
    resume_file: Optional[UploadFile] = File(None),
    linkedin_profile: Optional[UploadFile] = File(None),
    current_user: str = Depends(get_current_user)
):
    return await handle_create_student_data(career_goals, resume_file, linkedin_profile, current_user)

@router.post("/company-data", response_model=CompanyDataResponse)
async def create_company_data(
    company_name: str = Form(...),
    company_description: str = Form(...),
    website_urls: str = Form(default=""),
    company_data_file: Optional[UploadFile] = File(None),
    current_user: str = Depends(get_current_user)
):
    return await handle_create_company_data(company_name, company_description, website_urls, company_data_file, current_user)


@router.post("/job-data", response_model=JobDataResponse)
async def create_job_data(
    job_request: JobDataCreate,
    current_user: str = Depends(get_current_user)
):
    return await handle_create_job_data(job_request, current_user)


@router.post("/analyze-compatibility", response_model=AnalysisResponse)
async def analyze_compatibility(
    analysis_request: AnalysisRequest,
    current_user: str = Depends(get_current_user)
):
    return await handle_analyze_compatibility(analysis_request, current_user)


@router.get("/student-data", response_model=StudentDataResponse)
async def get_student_data(current_user: str = Depends(get_current_user)):
    return await handle_get_student_data(current_user)


@router.get("/company-data", response_model=CompanyDataResponse)
async def get_company_data(current_user: str = Depends(get_current_user)):
    return await handle_get_company_data(current_user)


@router.get("/jobs", response_model=list[JobDataResponse])
async def get_company_jobs(current_user: str = Depends(get_current_user)):
    return await handle_get_company_jobs(current_user)
