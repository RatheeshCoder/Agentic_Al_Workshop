# main.py
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import tempfile
import uvicorn
from typing import Dict, Any

from app.services.compatibility_service import CompatibilityService
from app.schemas.compatibility_schemas import (
    CompatibilityResponse, 
)

app = FastAPI(title="Candidate-Company Compatibility Navigator API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the service
compatibility_service = CompatibilityService()

# Response models
class AnalysisInitiatedResponse(BaseModel):
    message: str
    analysis_id: str
    status: str

class AnalysisResultResponse(BaseModel):
    analysis_id: str
    status: str
    data: Dict[str, Any]

@app.post("/analyze-compatibility", response_model=AnalysisInitiatedResponse)
async def analyze_compatibility(
    resume_file: UploadFile = File(...),
    linkedin_profile: UploadFile = File(None),
    career_goals: str = Form(...),
    company_data: UploadFile = File(...),
    job_descriptions: str = Form(...),
    company_urls: str = Form(default="")
):
    """
    Analyze candidate-company compatibility using 5 AI agents.
    Returns analysis ID instead of full results.
    """
    try:
        # Validate file types
        if not resume_file.filename.endswith(('.pdf', '.txt')):
            raise HTTPException(status_code=400, detail="Resume must be a PDF or TXT file")
        
        if not company_data.filename.endswith(('.pdf', '.txt')):
            raise HTTPException(status_code=400, detail="Company data must be a PDF or TXT file")
        
        # Save uploaded files temporarily
        temp_files = {}
        
        # Save resume
        if resume_file:
            suffix = '.pdf' if resume_file.filename.endswith('.pdf') else '.txt'
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                content = await resume_file.read()
                temp_file.write(content)
                temp_files['resume'] = temp_file.name
        
        # Save LinkedIn profile if provided
        if linkedin_profile:
            suffix = '.pdf' if linkedin_profile.filename.endswith('.pdf') else '.txt'
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                content = await linkedin_profile.read()
                temp_file.write(content)
                temp_files['linkedin'] = temp_file.name
        
        # Save company data
        if company_data:
            suffix = '.pdf' if company_data.filename.endswith('.pdf') else '.txt'
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                content = await company_data.read()
                temp_file.write(content)
                temp_files['company_data'] = temp_file.name
        
        try:
            # Prepare request data
            request_data = {
                'resume_path': temp_files.get('resume'),
                'linkedin_path': temp_files.get('linkedin'),
                'career_goals': career_goals,
                'company_data_path': temp_files.get('company_data'),
                'job_descriptions': job_descriptions,
                'company_urls': company_urls.split(',') if company_urls else []
            }
            
            # Run the compatibility analysis and get ID
            analysis_id = await compatibility_service.analyze_compatibility(request_data)
            
            if not analysis_id:
                raise HTTPException(status_code=500, detail="Failed to initiate analysis")
            
            return AnalysisInitiatedResponse(
                message="Compatibility analysis completed successfully",
                analysis_id=analysis_id,
                status="completed"
            )
            
        finally:
            # Clean up temp files
            for file_path in temp_files.values():
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/analysis/{analysis_id}", response_model=AnalysisResultResponse)
async def get_analysis_result(
    analysis_id: str = Path(..., description="The analysis ID returned from the POST endpoint")
):
    """
    Retrieve the complete compatibility analysis result by ID
    """
    try:
        # Validate ObjectId format
        if len(analysis_id) != 24:
            raise HTTPException(status_code=400, detail="Invalid analysis ID format")
        
        # Get analysis result from database
        result = await compatibility_service.get_analysis_by_id(analysis_id)
        
        return AnalysisResultResponse(
            analysis_id=analysis_id,
            status="completed",
            data=result
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve analysis: {str(e)}")

@app.get("/analysis/{analysis_id}/summary")
async def get_analysis_summary(
    analysis_id: str = Path(..., description="The analysis ID returned from the POST endpoint")
):
    """
    Retrieve a summary of the compatibility analysis result by ID
    """
    try:
        # Validate ObjectId format
        if len(analysis_id) != 24:
            raise HTTPException(status_code=400, detail="Invalid analysis ID format")
        
        # Get analysis result from database
        result = await compatibility_service.get_analysis_by_id(analysis_id)
        
        # Extract summary information
        summary = {
            "analysis_id": analysis_id,
            "overall_score": result.get("compatibility_score", {}).get("overall_score", 0),
            "intent_alignment": result.get("compatibility_score", {}).get("intent_alignment", 0),
            "skill_match": result.get("compatibility_score", {}).get("skill_match", 0),
            "cultural_fit": result.get("compatibility_score", {}).get("cultural_fit", 0),
            "confidence": result.get("compatibility_score", {}).get("metadata", {}).get("confidence", "medium"),
            "created_at": result.get("created_at"),
            "match_reasoning": result.get("counseling_report", {}).get("match_reasoning", ""),
            "matched_skills_count": len(result.get("skill_alignment", {}).get("matched_skills", [])),
            "skill_gaps_count": len(result.get("skill_alignment", {}).get("skill_gaps", [])),
            "status": result.get("status", "completed")
        }
        
        return JSONResponse(content=summary)
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve analysis summary: {str(e)}")

@app.get("/")
async def root():
    return {
        "message": "Candidate-Company Compatibility Navigator API is running!",
        "version": "1.0.0",
        "endpoints": {
            "POST /analyze-compatibility": "Submit files and data for compatibility analysis",
            "GET /analysis/{analysis_id}": "Retrieve complete analysis results by ID",
            "GET /analysis/{analysis_id}/summary": "Retrieve analysis summary by ID"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # You can add database connectivity check here if needed
        return {
            "status": "healthy",
            "service": "Compatibility Navigator API",
            "timestamp": "2024-12-20T10:00:00Z"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)