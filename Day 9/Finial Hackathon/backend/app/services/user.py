import uuid
import tempfile
from datetime import datetime
from fastapi import HTTPException, UploadFile
from typing import Optional
from app.database.connection import get_async_collections
from app.models.user_model import StudentDataResponse, CompanyDataResponse, JobDataCreate, JobDataResponse, AnalysisRequest, AnalysisResponse

async def handle_create_student_data(career_goals, resume_file, linkedin_profile, current_user):
    collections = get_async_collections()
    student_id = str(uuid.uuid4())
    temp_files = {}

    # Save files
    for label, file in [('resume', resume_file), ('linkedin', linkedin_profile)]:
        if file and file.filename:
            if not file.filename.endswith(('.pdf', '.txt', '.docx')):
                raise HTTPException(status_code=400, detail=f"{label.capitalize()} must be a PDF, TXT, or DOCX file")
            suffix = '.' + file.filename.split('.')[-1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
                content = await file.read()
                temp.write(content)
                temp_files[label] = temp.name

    existing_data = await collections["student_data"].find_one({"user_id": current_user})

    student_data = {
        "id": student_id,
        "user_id": current_user,
        "career_goals": career_goals,
        "resume_path": temp_files.get('resume'),
        "linkedin_path": temp_files.get('linkedin'),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    if existing_data:
        await collections["student_data"].update_one(
            {"user_id": current_user},
            {"$set": {
                "career_goals": career_goals,
                "resume_path": temp_files.get('resume', existing_data.get('resume_path')),
                "linkedin_path": temp_files.get('linkedin', existing_data.get('linkedin_path')),
                "updated_at": datetime.utcnow()
            }}
        )
        student_data["id"] = existing_data["id"]
        student_data["created_at"] = existing_data["created_at"]
    else:
        await collections["student_data"].insert_one(student_data)

    return StudentDataResponse(**student_data)


async def handle_create_company_data(company_name, company_description, website_urls, company_data_file, current_user):
    collections = get_async_collections()
    company_id = str(uuid.uuid4())
    temp_files = {}

    # URLs
    url_list = [url.strip() for url in website_urls.split(',') if url.strip()] if website_urls else []

    # File
    if company_data_file and company_data_file.filename:
        if not company_data_file.filename.endswith(('.pdf', '.txt', '.docx')):
            raise HTTPException(status_code=400, detail="Company data file must be a PDF, TXT, or DOCX file")
        suffix = '.' + company_data_file.filename.split('.')[-1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            content = await company_data_file.read()
            temp.write(content)
            temp_files['company_data'] = temp.name

    existing_data = await collections["company_data"].find_one({"user_id": current_user})

    company_data = {
        "id": company_id,
        "user_id": current_user,
        "company_name": company_name,
        "company_description": company_description,
        "website_urls": url_list,
        "company_data_path": temp_files.get('company_data'),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    if existing_data:
        await collections["company_data"].update_one(
            {"user_id": current_user},
            {"$set": {
                "company_name": company_name,
                "company_description": company_description,
                "website_urls": url_list,
                "company_data_path": temp_files.get('company_data', existing_data.get('company_data_path')),
                "updated_at": datetime.utcnow()
            }}
        )
        company_data["id"] = existing_data["id"]
        company_data["created_at"] = existing_data["created_at"]
    else:
        await collections["company_data"].insert_one(company_data)

    return CompanyDataResponse(**company_data)


async def handle_create_job_data(job_request, current_user):
    collections = get_async_collections()
    company_data = await collections["company_data"].find_one({
        "id": job_request.company_id,
        "user_id": current_user
    })

    if not company_data:
        raise HTTPException(status_code=404, detail="Company not found or you don't have permission")

    job_id = str(uuid.uuid4())
    job_data = {
        "id": job_id,
        "company_id": job_request.company_id,
        "job_title": job_request.job_title,
        "job_description": job_request.job_description,
        "requirements": job_request.requirements,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    await collections["job_data"].insert_one(job_data)
    return JobDataResponse(**job_data)


async def handle_analyze_compatibility(analysis_request, current_user):
    collections = get_async_collections()
    analysis_id = str(uuid.uuid4())

    student_data = await collections["student_data"].find_one({"user_id": current_user})
    if not student_data:
        raise HTTPException(status_code=404, detail="Student data not found.")

    job_data = await collections["job_data"].find_one({"id": analysis_request.job_id})
    if not job_data:
        raise HTTPException(status_code=404, detail="Job not found")

    company_data = await collections["company_data"].find_one({"id": job_data["company_id"]})
    if not company_data:
        raise HTTPException(status_code=404, detail="Company data not found")

    analysis_data = {
        "analysis_id": analysis_id,
        "student_id": current_user,
        "job_id": analysis_request.job_id,
        "company_id": job_data["company_id"],
        "student_data": {
            "career_goals": student_data["career_goals"],
            "resume_path": student_data.get("resume_path"),
            "linkedin_path": student_data.get("linkedin_path")
        },
        "job_data": {
            "job_title": job_data["job_title"],
            "job_description": job_data["job_description"],
            "requirements": job_data["requirements"]
        },
        "company_data": {
            "company_name": company_data["company_name"],
            "company_description": company_data["company_description"],
            "website_urls": company_data["website_urls"],
            "company_data_path": company_data.get("company_data_path")
        },
        "status": "processing",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    await collections["compatibility_results"].insert_one(analysis_data)

    # Trigger compatibility analysis agent here (asynchronously)

    return AnalysisResponse(
        message="Compatibility analysis initiated successfully",
        analysis_id=analysis_id,
        status="processing"
    )


async def handle_get_student_data(current_user):
    collections = get_async_collections()
    student_data = await collections["student_data"].find_one({"user_id": current_user})
    if not student_data:
        raise HTTPException(status_code=404, detail="Student data not found")
    return StudentDataResponse(**student_data)


async def handle_get_company_data(current_user):
    collections = get_async_collections()
    company_data = await collections["company_data"].find_one({"user_id": current_user})
    if not company_data:
        raise HTTPException(status_code=404, detail="Company data not found")
    return CompanyDataResponse(**company_data)


async def handle_get_company_jobs(current_user):
    collections = get_async_collections()
    company_data = await collections["company_data"].find_one({"user_id": current_user})
    if not company_data:
        raise HTTPException(status_code=404, detail="Company data not found")

    jobs_cursor = collections["job_data"].find({"company_id": company_data["id"]})
    jobs = await jobs_cursor.to_list(length=None)

    return [JobDataResponse(**job) for job in jobs]
