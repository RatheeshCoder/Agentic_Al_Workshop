from typing import Dict, Any
from langgraph.graph import StateGraph, END , START
from app.rag.rag_processor import CompatibilityState
from app.agents.agents import (student_intent_analyzer_agent, company_culture_extractor_agent,
                    skill_role_alignment_agent, fit_scorer_agent, counselor_agent)
from app.rag.rag_processor import RAGProcessor

class CompatibilityService:
    def __init__(self):
        self.graph = self.build_compatibility_graph()
        self.rag_processor = RAGProcessor()
    
    def build_compatibility_graph(self) -> StateGraph:
        graph_builder = StateGraph(CompatibilityState)
        
        graph_builder.add_node("student_intent_analyzer", student_intent_analyzer_agent)
        graph_builder.add_node("company_culture_extractor", company_culture_extractor_agent)
        graph_builder.add_node("skill_role_alignment", skill_role_alignment_agent)
        graph_builder.add_node("fit_scorer", fit_scorer_agent)
        graph_builder.add_node("counselor", counselor_agent)
        
        graph_builder.add_edge(START ,"student_intent_analyzer")
        graph_builder.add_edge("student_intent_analyzer", "company_culture_extractor")
        graph_builder.add_edge("company_culture_extractor", "skill_role_alignment")
        graph_builder.add_edge("skill_role_alignment", "fit_scorer")
        graph_builder.add_edge("fit_scorer", "counselor")
        graph_builder.add_edge("counselor", END)
        
        return graph_builder.compile()

    async def analyze_compatibility(self, request_data: Dict[str, Any]) -> str:
        print("🚀 Starting Compatibility Analysis...")
        
        required_fields = ["resume_path", "career_goals", "company_data_path", "job_descriptions"]
        for field in required_fields:
            if field not in request_data:
                raise ValueError(f"Missing required field: {field}")
        
        initial_state: CompatibilityState = {
            "resume_path": request_data["resume_path"],
            "linkedin_path": request_data.get("linkedin_path", ""),
            "career_goals": request_data["career_goals"],
            "company_data_path": request_data["company_data_path"],
            "job_descriptions": request_data["job_descriptions"],
            "company_urls": request_data.get("company_urls", []),
            "student_intents": {},
            "company_culture": {},
            "skill_alignment": {},
            "compatibility_score": {},
            "counseling_report": {},
            "resume_chunks": [],
            "company_chunks": []
        }
        
        final_state = await self.graph.ainvoke(initial_state)
        
        analysis_result = {
            "input_data": {
                "career_goals": request_data["career_goals"],
                "job_descriptions": request_data["job_descriptions"],
                "company_urls": request_data.get("company_urls", [])
            },
            "student_intents": final_state["student_intents"],
            "company_culture": final_state["company_culture"],
            "skill_alignment": final_state["skill_alignment"],
            "compatibility_score": final_state["compatibility_score"],
            "counseling_report": final_state["counseling_report"],
            "analysis_summary": f"""
            Compatibility Analysis Complete!
            
            Overall Score: {final_state["compatibility_score"]["overall_score"]}%
            - Intent Alignment: {final_state["compatibility_score"]["intent_alignment"]}%
            - Skill Match: {final_state["compatibility_score"]["skill_match"]}%
            - Cultural Fit: {final_state["compatibility_score"]["cultural_fit"]}%
            
            Key Insights:
            - Matched Skills: {len(final_state["skill_alignment"]["matched_skills"])}
            - Skill Gaps: {len(final_state["skill_alignment"]["skill_gaps"])}
            - Hidden Opportunities: {len(final_state["skill_alignment"]["hidden_opportunities"])}
            
            Recommendation: {final_state["counseling_report"]["match_reasoning"]}
            """
        }
        
        analysis_id = self.rag_processor.save_analysis_result(analysis_result)
        
        if not analysis_id:
            raise Exception("Failed to save analysis result to database")
        
        print("✅ Analysis completed and saved!")
        return analysis_id
    
    async def get_analysis_by_id(self, analysis_id: str) -> Dict[str, Any]:
        print(f"🔍 Retrieving analysis for ID: {analysis_id}")
        
        result = self.rag_processor.get_analysis_result(analysis_id)
        
        if not result:
            raise ValueError(f"No analysis found for ID: {analysis_id}")
        
        return result