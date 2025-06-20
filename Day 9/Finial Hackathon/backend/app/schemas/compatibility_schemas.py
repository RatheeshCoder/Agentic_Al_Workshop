from pydantic import BaseModel,Field
from typing import List, Dict, Any, Optional 
from datetime import datetime

class StudentIntents(BaseModel):
    desired_industries: List[str]
    preferred_culture: List[str]
    work_preferences: List[str]
    learning_goals: List[str]
    career_aspirations: List[str]
    
class CompanyCulture(BaseModel):
    values: List[str]
    work_life_balance: str
    learning_support: List[str]
    team_culture: str
    company_size: str
    
class SkillAlignment(BaseModel):
    matched_skills: List[str]
    skill_gaps: List[str]
    hidden_opportunities: List[str]
    transferable_skills: List[str]
    
class CompatibilityScore(BaseModel):
    overall_score: int
    intent_alignment: int
    skill_match: int
    cultural_fit: int
    metadata: Dict[str, Any]
    
class CounselingReport(BaseModel):
    match_reasoning: str
    alternative_suggestions: List[str]
    actionable_advice: List[str]
    skill_development_plan: List[str]

class CompatibilityRequest(BaseModel):
    resume_path: str
    linkedin_path: Optional[str] = None
    career_goals: str
    company_data_path: str
    job_descriptions: str
    company_urls: List[str] = []

class CompatibilityResponse(BaseModel):
    student_intents: StudentIntents
    company_culture: CompanyCulture
    skill_alignment: SkillAlignment
    compatibility_score: CompatibilityScore
    counseling_report: CounselingReport
    analysis_summary: str

# Request models for API
class AnalysisRequest(BaseModel):
    career_goals: str = Field(..., description="Career goals and aspirations")
    job_descriptions: str = Field(..., description="Job descriptions to analyze against")
    company_urls: Optional[List[str]] = Field(default_factory=list, description="Company URLs for additional context")

# Response models for new API structure
class AnalysisInitiatedResponse(BaseModel):
    message: str
    analysis_id: str
    status: str

class AnalysisResultResponse(BaseModel):
    analysis_id: str
    status: str
    data: Dict[str, Any]

class AnalysisSummaryResponse(BaseModel):
    analysis_id: str
    overall_score: int
    intent_alignment: int
    skill_match: int
    cultural_fit: int
    confidence: str
    created_at:str
    match_reasoning: str
    matched_skills_count: int
    skill_gaps_count: int
    status: str