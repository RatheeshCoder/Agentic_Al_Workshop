from typing import TypedDict, List, Dict

class AgentState(TypedDict):
    pdf_path: str
    target_role: str
    student_skills: List[str]
    student_education: str
    student_experience: str
    student_projects: str
    industry_requirements: str
    industry_skills: List[str]
    matched_skills: List[str]
    missing_skills: List[str]
    alignment_score: int
    recommendations: Dict[str, List[str]]
