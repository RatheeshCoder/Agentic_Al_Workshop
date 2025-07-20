import os
from typing import Optional, List, Tuple
import uuid
import aiofiles
from datetime import datetime
from fastapi import APIRouter, Form, File, UploadFile, Depends, HTTPException, staticfiles
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path

# Create router
router = APIRouter()

# Configuration
UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'.pdf', '.txt', '.docx', '.doc'}

os.makedirs(UPLOAD_DIR, exist_ok=True)



def validate_file(file: UploadFile, file_type: str) -> None:
    """Validate uploaded file"""
    if not file.filename:
        raise HTTPException(status_code=400, detail=f"{file_type} filename is required")
    
    # Check file extension
    file_extension = os.path.splitext(file.filename)[1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"{file_type} must be a PDF or TXT file"
        )

async def save_uploaded_file(file: UploadFile, user_id: str, file_type: str) -> tuple[str, str]:
    """
    Save uploaded file and return both file path and URL
    Returns: (file_path, file_url)
    """
    if not file or not file.filename:
        return None, None
    
    # Validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB")
    
    # Reset file position
    await file.seek(0)
    
    # Validate file extension
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"{file_type.capitalize()} must be one of: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Generate unique filename
    unique_filename = f"{user_id}_{file_type}_{uuid.uuid4().hex}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Save file using aiofiles
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save {file_type} file: {str(e)}")
    
    # Generate URL for frontend access
    file_url = f"/uploads/{unique_filename}"
    
    return file_path, file_url

async def delete_old_file(file_path: str):
    """Delete old file if it exists"""
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Warning: Failed to delete old file {file_path}: {e}")

async def handle_create_student_data(career_goals, resume_file, linkedin_profile, current_user):
    collections = get_async_collections()
    student_id = str(uuid.uuid4())
    
    # Get existing data to handle file replacements
    existing_data = await collections["student_data"].find_one({"user_id": current_user})
    
    # Initialize file paths and URLs
    resume_path, resume_url = None, None
    linkedin_path, linkedin_url = None, None
    
    try:
        # Handle resume file
        if resume_file and resume_file.filename:
            # Delete old resume if exists
            if existing_data and existing_data.get('resume_path'):
                await delete_old_file(existing_data['resume_path'])
            
            resume_path, resume_url = await save_uploaded_file(resume_file, current_user, 'resume')
        elif existing_data:
            # Keep existing resume
            resume_path = existing_data.get('resume_path')
            resume_url = existing_data.get('resume_url')
        
        # Handle LinkedIn profile file
        if linkedin_profile and linkedin_profile.filename:
            # Delete old LinkedIn file if exists
            if existing_data and existing_data.get('linkedin_path'):
                await delete_old_file(existing_data['linkedin_path'])
            
            linkedin_path, linkedin_url = await save_uploaded_file(linkedin_profile, current_user, 'linkedin')
        elif existing_data:
            # Keep existing LinkedIn file
            linkedin_path = existing_data.get('linkedin_path')
            linkedin_url = existing_data.get('linkedin_url')
        
        # Prepare student data
        student_data = {
            "id": student_id,
            "user_id": current_user,
            "career_goals": career_goals,
            "resume_path": resume_path,
            "linkedin_path": linkedin_path,
            "resume_url": resume_url,
            "linkedin_url": linkedin_url,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        if existing_data:
            # Update existing record
            await collections["student_data"].update_one(
                {"user_id": current_user},
                {"$set": {
                    "career_goals": career_goals,
                    "resume_path": resume_path,
                    "linkedin_path": linkedin_path,
                    "resume_url": resume_url,
                    "linkedin_url": linkedin_url,
                    "updated_at": datetime.utcnow()
                }}
            )
            student_data["id"] = existing_data["id"]
            student_data["created_at"] = existing_data["created_at"]
        else:
            # Insert new record
            await collections["student_data"].insert_one(student_data)
        
        return StudentDataResponse(**student_data)
        
    except Exception as e:
        # Cleanup uploaded files if database operation fails
        if resume_path and os.path.exists(resume_path):
            await delete_old_file(resume_path)
        if linkedin_path and os.path.exists(linkedin_path):
            await delete_old_file(linkedin_path)
        raise e



def cleanup_files(file_paths: List[str]) -> int:
    """Clean up temporary files and return count of files removed"""
    removed_count = 0
    
    for file_path in file_paths:
        if file_path and os.path.exists(file_path):
            try:
                os.unlink(file_path)
                removed_count += 1
            except Exception as e:
                print(f"Warning: Could not delete temp file {file_path}: {e}")
    
    return removed_count

def get_file_paths_from_analysis(analysis_data: dict) -> List[str]:
    """Extract file paths from analysis data"""
    file_paths = []
    
    # Add file paths based on analysis type
    if analysis_data.get("resume_path"):
        file_paths.append(analysis_data["resume_path"])
    
    if analysis_data.get("linkedin_path"):
        file_paths.append(analysis_data["linkedin_path"])
    
    if analysis_data.get("company_data_path"):
        file_paths.append(analysis_data["company_data_path"])
    
    return file_paths