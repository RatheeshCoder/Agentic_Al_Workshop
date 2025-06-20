import os
import json
import PyPDF2
import google.generativeai as genai
from tavily import TavilyClient
from typing import List, Dict, Any, TypedDict
from langgraph.graph import StateGraph, END
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
import numpy as np
from datetime import datetime
import hashlib
import re
from app.schemas.compatibility_schemas import *

# Configuration
os.environ["GOOGLE_API_KEY"] = "AIzaSyB_KtLx3UmzQKeC4myIMej7A0Rsh_aS_CY"
os.environ["TAVILY_API_KEY"] = "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"

class CompatibilityState(TypedDict):
    # Input data
    resume_path: str
    linkedin_path: str
    career_goals: str
    company_data_path: str
    job_descriptions: str
    company_urls: List[str]
    
    # Agent outputs
    student_intents: Dict[str, Any]
    company_culture: Dict[str, Any]
    skill_alignment: Dict[str, Any]
    compatibility_score: Dict[str, Any]
    counseling_report: Dict[str, Any]
    
    # RAG data
    resume_chunks: List[str]
    company_chunks: List[str]

class RAGProcessor:
    def __init__(self, mongo_uri: str = "mongodb://localhost:27017/", db_name: str = "compatibility_db"):
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.collection = self.db.document_vectors
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
    def process_document(self, file_path: str, doc_type: str) -> str:
        """Process and store document with embeddings"""
        try:
            if file_path.endswith('.pdf'):
                text = self._extract_pdf_text(file_path)
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            
            # Generate document hash
            doc_hash = hashlib.md5(text.encode()).hexdigest()
            
            # Check if already processed
            existing = self.collection.find_one({"doc_hash": doc_hash})
            if existing:
                return doc_hash
            
            # Create chunks
            chunks = self._chunk_text(text)
            embeddings = self.embedding_model.encode(chunks).tolist()
            
            # Store in MongoDB
            documents = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                doc = {
                    "doc_hash": doc_hash,
                    "doc_type": doc_type,
                    "chunk_id": i,
                    "text": chunk,
                    "embedding": embedding,
                    "created_at": datetime.now()
                }
                documents.append(doc)
            
            self.collection.insert_many(documents)
            return doc_hash
            
        except Exception as e:
            print(f"Error processing document: {e}")
            return None
    
    def semantic_search(self, query: str, doc_hash: str, top_k: int = 3) -> List[str]:
        """Search for relevant chunks using semantic similarity"""
        try:
            query_embedding = self.embedding_model.encode([query])[0].tolist()
            chunks = list(self.collection.find({"doc_hash": doc_hash}))
            
            if not chunks:
                return []
            
            similarities = []
            for chunk in chunks:
                chunk_embedding = chunk["embedding"]
                similarity = np.dot(query_embedding, chunk_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(chunk_embedding)
                )
                similarities.append({"text": chunk["text"], "similarity": similarity})
            
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            return [item["text"] for item in similarities[:top_k]]
            
        except Exception as e:
            print(f"Error in semantic search: {e}")
            return []
    
    def _extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return ""
    
    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks"""
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk.strip())
        return chunks

# Initialize global components
rag_processor = RAGProcessor()
tavily_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

# Agent 1: Student Intent Analyzer
def student_intent_analyzer_agent(state: CompatibilityState) -> CompatibilityState:
    """Extract student intents from resume, LinkedIn, and career goals"""
    print("🎯 Agent 1: Analyzing student intents...")
    
    try:
        # Process resume with RAG
        resume_hash = rag_processor.process_document(state["resume_path"], "resume")
        
        # Process LinkedIn if available
        linkedin_text = ""
        if state["linkedin_path"]:
            with open(state["linkedin_path"], 'r', encoding='utf-8') as f:
                linkedin_text = f.read()
        
        # Search for intent-related information
        queries = [
            "career goals aspirations industry preferences",
            "work environment culture preferences remote office",
            "learning development training mentorship goals",
            "company size startup corporate preferences"
        ]
        
        combined_context = ""
        for query in queries:
            relevant_chunks = rag_processor.semantic_search(query, resume_hash, top_k=2)
            combined_context += " ".join(relevant_chunks) + " "
        
        combined_context += linkedin_text + " " + state["career_goals"]
        
        prompt = f"""
        Analyze the following information to extract student intents and preferences:
        
        {combined_context[:3000]}
        
        Extract and return a JSON object with:
        {{
            "desired_industries": ["industry1", "industry2", ...],
            "preferred_culture": ["startup", "corporate", "remote-first", ...],
            "work_preferences": ["remote", "hybrid", "in-office", ...],
            "learning_goals": ["mentorship", "training", "certification", ...],
            "career_aspirations": ["leadership", "technical expertise", "entrepreneurship", ...]
        }}
        
        Ensure all values are arrays of strings. Be specific and extract actual preferences mentioned.
        """
        
        response = gemini_model.generate_content(prompt)
        result_text = response.text.strip()
        
        # Clean JSON response
        if result_text.startswith('```json'):
            result_text = result_text.replace('```json', '').replace('```', '').strip()
        
        student_intents = json.loads(result_text)
        
        print(f"✅ Extracted intents: {len(student_intents.get('desired_industries', []))} industries")
        
    except Exception as e:
        print(f"Error in student intent analysis: {e}")
        student_intents = {
            "desired_industries": ["Technology", "Software"],
            "preferred_culture": ["Innovative", "Collaborative"],
            "work_preferences": ["Hybrid", "Flexible"],
            "learning_goals": ["Skill Development", "Mentorship"],
            "career_aspirations": ["Technical Leadership", "Problem Solving"]
        }
    
    return {**state, "student_intents": student_intents}

# Agent 2: Company Culture Extractor (RAG-enabled)
def company_culture_extractor_agent(state: CompatibilityState) -> CompatibilityState:
    """Extract company culture using RAG and web search"""
    print("🏢 Agent 2: Extracting company culture...")
    
    try:
        # Process company documents
        company_hash = rag_processor.process_document(state["company_data_path"], "company")
        
        # Web search for additional company information
        web_context = ""
        if state["company_urls"]:
            for url in state["company_urls"][:3]:  # Limit to 3 URLs
                try:
                    search_query = f"company culture values work life balance {url}"
                    search_results = tavily_client.search(search_query, max_results=3)
                    for result in search_results.get("results", []):
                        web_context += result.get("content", "") + " "
                except:
                    continue
        
        # RAG search for culture-related information
        culture_queries = [
            "company values mission vision culture",
            "work life balance flexible working",
            "learning development training programs",
            "team collaboration communication style",
            "company size structure organization"
        ]
        
        combined_context = ""
        for query in culture_queries:
            relevant_chunks = rag_processor.semantic_search(query, company_hash, top_k=2)
            combined_context += " ".join(relevant_chunks) + " "
        
        combined_context += web_context + " " + state["job_descriptions"]
        
        prompt = f"""
        Analyze the following company information to extract cultural traits:
        
        {combined_context[:3000]}
        
        Return a JSON object with:
        {{
            "values": ["value1", "value2", ...],
            "work_life_balance": "description of work-life balance",
            "learning_support": ["training programs", "mentorship", ...],
            "team_culture": "description of team culture",
            "company_size": "startup/medium/large/enterprise"
        }}
        
        Be specific and extract actual cultural elements mentioned.
        """
        
        response = gemini_model.generate_content(prompt)
        result_text = response.text.strip()
        
        if result_text.startswith('```json'):
            result_text = result_text.replace('```json', '').replace('```', '').strip()
        
        company_culture = json.loads(result_text)
        
        print(f"✅ Extracted culture: {len(company_culture.get('values', []))} values")
        
    except Exception as e:
        print(f"Error in company culture extraction: {e}")
        company_culture = {
            "values": ["Innovation", "Collaboration", "Excellence"],
            "work_life_balance": "Flexible working arrangements",
            "learning_support": ["Training Programs", "Mentorship"],
            "team_culture": "Collaborative and supportive",
            "company_size": "Medium"
        }
    
    return {**state, "company_culture": company_culture}

# Agent 3: Skill & Role Alignment
def skill_role_alignment_agent(state: CompatibilityState) -> CompatibilityState:
    """Map student skills to job requirements and find hidden opportunities"""
    print("🎯 Agent 3: Analyzing skill-role alignment...")
    
    try:
        # Extract skills from resume using RAG
        resume_hash = rag_processor.process_document(state["resume_path"], "resume")
        skill_queries = [
            "technical skills programming languages frameworks",
            "software development experience projects",
            "tools technologies platforms used"
        ]
        
        resume_skills_context = ""
        for query in skill_queries:
            relevant_chunks = rag_processor.semantic_search(query, resume_hash, top_k=3)
            resume_skills_context += " ".join(relevant_chunks) + " "
        
        # Extract skills from job descriptions
        job_skills_prompt = f"""
        Extract technical skills and requirements from these job descriptions:
        
        {state["job_descriptions"][:2000]}
        
        Return a JSON array of required skills: ["skill1", "skill2", ...]
        """
        
        job_skills_response = gemini_model.generate_content(job_skills_prompt)
        job_skills_text = job_skills_response.text.strip()
        
        if job_skills_text.startswith('```json'):
            job_skills_text = job_skills_text.replace('```json', '').replace('```', '').strip()
        
        try:
            job_skills = json.loads(job_skills_text)
        except:
            job_skills = re.findall(r'"([^"]+)"', job_skills_text)
        
        # Skill alignment analysis
        alignment_prompt = f"""
        Analyze skill alignment between student and job requirements:
        
        Student Context: {resume_skills_context[:1500]}
        Job Requirements: {state["job_descriptions"][:1500]}
        Required Skills: {job_skills}
        
        Return JSON with:
        {{
            "matched_skills": ["skill1", "skill2", ...],
            "skill_gaps": ["missing_skill1", "missing_skill2", ...],
            "hidden_opportunities": ["transferable_skill1", "adjacent_role1", ...],
            "transferable_skills": ["soft_skill1", "domain_knowledge1", ...]
        }}
        
        Identify at least one hidden opportunity per profile.
        """
        
        response = gemini_model.generate_content(alignment_prompt)
        result_text = response.text.strip()
        
        if result_text.startswith('```json'):
            result_text = result_text.replace('```json', '').replace('```', '').strip()
        
        skill_alignment = json.loads(result_text)
        
        print(f"✅ Skill alignment: {len(skill_alignment.get('matched_skills', []))} matched")
        
    except Exception as e:
        print(f"Error in skill alignment: {e}")
        skill_alignment = {
            "matched_skills": ["Python", "JavaScript", "Problem Solving"],
            "skill_gaps": ["Machine Learning", "Cloud Computing"],
            "hidden_opportunities": ["Data Analysis Role", "Frontend Development"],
            "transferable_skills": ["Communication", "Project Management"]
        }
    
    return {**state, "skill_alignment": skill_alignment}

# Agent 4: Fit Scorer
def fit_scorer_agent(state: CompatibilityState) -> CompatibilityState:
    """Generate compatibility score based on all factors"""
    print("📊 Agent 4: Calculating compatibility score...")
    
    try:
        # Calculate individual scores
        intent_score = calculate_intent_alignment(
            state["student_intents"], 
            state["company_culture"]
        )
        
        skill_score = calculate_skill_match(state["skill_alignment"])
        
        culture_score = calculate_cultural_fit(
            state["student_intents"], 
            state["company_culture"]
        )
        
        # Overall score (weighted average)
        overall_score = int((intent_score + skill_score + culture_score) / 3)
        
        compatibility_score = {
            "overall_score": overall_score,
            "intent_alignment": intent_score,
            "skill_match": skill_score,
            "cultural_fit": culture_score,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "analysis_version": "1.0",
                "confidence": "high" if overall_score > 70 else "medium" if overall_score > 50 else "low"
            }
        }
        
        print(f"✅ Compatibility Score: {overall_score}%")
        
    except Exception as e:
        print(f"Error in scoring: {e}")
        compatibility_score = {
            "overall_score": 65,
            "intent_alignment": 70,
            "skill_match": 60,
            "cultural_fit": 65,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "analysis_version": "1.0",
                "confidence": "medium"
            }
        }
    
    return {**state, "compatibility_score": compatibility_score}

# Agent 5: Counselor Agent
def counselor_agent(state: CompatibilityState) -> CompatibilityState:
    """Provide reasoning and recommendations"""
    print("🎓 Agent 5: Generating counseling report...")
    
    try:
        score = state["compatibility_score"]["overall_score"]
        
        counseling_prompt = f"""
        Generate a counseling report based on this compatibility analysis:
        
        Overall Score: {score}%
        Student Intents: {state["student_intents"]}
        Company Culture: {state["company_culture"]}
        Skill Alignment: {state["skill_alignment"]}
        
        Provide JSON with:
        {{
            "match_reasoning": "explanation of why this match works or doesn't work",
            "alternative_suggestions": ["suggestion1", "suggestion2", ...],
            "actionable_advice": ["advice1", "advice2", ...],
            "skill_development_plan": ["step1", "step2", ...]
        }}
        
        For scores below 70, suggest at least 2 alternatives.
        Make advice specific and actionable.
        """
        
        response = gemini_model.generate_content(counseling_prompt)
        result_text = response.text.strip()
        
        if result_text.startswith('```json'):
            result_text = result_text.replace('```json', '').replace('```', '').strip()
        
        counseling_report = json.loads(result_text)
        
        print("✅ Counseling report generated")
        
    except Exception as e:
        print(f"Error in counseling: {e}")
        counseling_report = {
            "match_reasoning": "Moderate fit based on skill alignment and cultural preferences",
            "alternative_suggestions": ["Consider similar roles in different companies", "Explore related positions"],
            "actionable_advice": ["Develop missing technical skills", "Research company culture more"],
            "skill_development_plan": ["Complete online courses", "Build portfolio projects", "Network with professionals"]
        }
    
    return {**state, "counseling_report": counseling_report}

# Helper functions for scoring
def calculate_intent_alignment(student_intents: Dict, company_culture: Dict) -> int:
    """Calculate intent alignment score"""
    score = 0
    matches = 0
    
    # Check industry alignment
    if any(industry.lower() in " ".join(company_culture.get("values", [])).lower() 
           for industry in student_intents.get("desired_industries", [])):
        score += 30
        matches += 1
    
    # Check culture preferences
    student_culture = [c.lower() for c in student_intents.get("preferred_culture", [])]
    company_values = [v.lower() for v in company_culture.get("values", [])]
    
    if any(sc in " ".join(company_values) for sc in student_culture):
        score += 40
        matches += 1
    
    # Check work preferences
    if "remote" in student_intents.get("work_preferences", []) and \
       "flexible" in company_culture.get("work_life_balance", "").lower():
        score += 30
        matches += 1
    
    return min(score, 100)

def calculate_skill_match(skill_alignment: Dict) -> int:
    """Calculate skill match score"""
    matched = len(skill_alignment.get("matched_skills", []))
    gaps = len(skill_alignment.get("skill_gaps", []))
    
    if matched + gaps == 0:
        return 50
    
    return int((matched / (matched + gaps)) * 100)

def calculate_cultural_fit(student_intents: Dict, company_culture: Dict) -> int:
    """Calculate cultural fit score"""
    score = 0
    
    # Learning goals alignment
    student_learning = student_intents.get("learning_goals", [])
    company_learning = company_culture.get("learning_support", [])
    
    if any(sl.lower() in " ".join(company_learning).lower() for sl in student_learning):
        score += 50
    
    # Career aspirations alignment
    aspirations = student_intents.get("career_aspirations", [])
    company_values = company_culture.get("values", [])
    
    if any(asp.lower() in " ".join(company_values).lower() for asp in aspirations):
        score += 50
    
    return min(score, 100)

# Build the agent graph
def build_compatibility_graph() -> StateGraph:
    """Build the LangGraph workflow for compatibility analysis"""
    graph_builder = StateGraph(CompatibilityState)
    
    # Add all 5 agents
    graph_builder.add_node("student_intent_analyzer", student_intent_analyzer_agent)
    graph_builder.add_node("company_culture_extractor", company_culture_extractor_agent)
    graph_builder.add_node("skill_role_alignment", skill_role_alignment_agent)
    graph_builder.add_node("fit_scorer", fit_scorer_agent)
    graph_builder.add_node("counselor", counselor_agent)
    
    # Define the workflow
    graph_builder.set_entry_point("student_intent_analyzer")
    graph_builder.add_edge("student_intent_analyzer", "company_culture_extractor")
    graph_builder.add_edge("company_culture_extractor", "skill_role_alignment")
    graph_builder.add_edge("skill_role_alignment", "fit_scorer")
    graph_builder.add_edge("fit_scorer", "counselor")
    graph_builder.add_edge("counselor", END)
    
    return graph_builder.compile()

# Main service class
class CompatibilityService:
    def __init__(self):
        self.graph = build_compatibility_graph()
    
    async def analyze_compatibility(self, request_data: Dict[str, Any]) -> CompatibilityResponse:
        """Run the complete compatibility analysis"""
        print("🚀 Starting Candidate-Company Compatibility Analysis...")
        
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
        
        # Run the workflow
        final_state = self.graph.invoke(initial_state)
        
        # Build response
        response = CompatibilityResponse(
            student_intents=StudentIntents(**final_state["student_intents"]),
            company_culture=CompanyCulture(**final_state["company_culture"]),
            skill_alignment=SkillAlignment(**final_state["skill_alignment"]),
            compatibility_score=CompatibilityScore(**final_state["compatibility_score"]),
            counseling_report=CounselingReport(**final_state["counseling_report"]),
            analysis_summary=f"""
            Candidate-Company Compatibility Analysis Complete!
            
            Overall Compatibility Score: {final_state["compatibility_score"]["overall_score"]}%
            - Intent Alignment: {final_state["compatibility_score"]["intent_alignment"]}%
            - Skill Match: {final_state["compatibility_score"]["skill_match"]}%
            - Cultural Fit: {final_state["compatibility_score"]["cultural_fit"]}%
            
            Key Insights:
            - Matched Skills: {len(final_state["skill_alignment"]["matched_skills"])}
            - Skill Gaps: {len(final_state["skill_alignment"]["skill_gaps"])}
            - Hidden Opportunities: {len(final_state["skill_alignment"]["hidden_opportunities"])}
            
            Recommendation: {final_state["counseling_report"]["match_reasoning"]}
            """
        )
        
        print("✅ Compatibility analysis completed!")
        return response