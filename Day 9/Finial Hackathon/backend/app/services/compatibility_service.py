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
from bson import ObjectId
from app.schemas.compatibility_schemas import *

# Configuration
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "AIzaSyB_KtLx3UmzQKeC4myIMej7A0Rsh_aS_CY")
os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY", "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")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

class CompatibilityState(TypedDict):
    resume_path: str
    linkedin_path: str
    career_goals: str
    company_data_path: str
    job_descriptions: str
    company_urls: List[str]
    student_intents: Dict[str, Any]
    company_culture: Dict[str, Any]
    skill_alignment: Dict[str, Any]
    compatibility_score: Dict[str, Any]
    counseling_report: Dict[str, Any]
    resume_chunks: List[str]
    company_chunks: List[str]

class RAGProcessor:
    def __init__(self, mongo_uri: str = MONGO_URI, db_name: str = "compatibility_db", 
                 chunk_size: int = 500, chunk_overlap: int = 50):
        self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[db_name]
        self.collection = self.db.document_vectors
        # Add results collection for storing analysis results
        self.results_collection = self.db.compatibility_results
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def __del__(self):
        self.client.close()

    def save_analysis_result(self, analysis_data: Dict[str, Any]) -> str:
        """Save the complete analysis result to MongoDB and return the ID"""
        try:
            # Add metadata
            analysis_data["created_at"] = datetime.now()
            analysis_data["status"] = "completed"
            
            # Insert the document
            result = self.results_collection.insert_one(analysis_data)
            
            print(f"✅ Analysis result saved with ID: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            print(f"Error saving analysis result: {e}")
            return None
    
    def get_analysis_result(self, analysis_id: str) -> Dict[str, Any]:
        """Retrieve analysis result by ID"""
        try:
            # Convert string ID to ObjectId
            object_id = ObjectId(analysis_id)
            
            # Find the document
            result = self.results_collection.find_one({"_id": object_id})
            
            if result:
                # Convert ObjectId to string for JSON serialization
                result["_id"] = str(result["_id"])
                print(f"✅ Analysis result retrieved for ID: {analysis_id}")
                return result
            else:
                print(f"❌ No analysis found for ID: {analysis_id}")
                return None
                
        except Exception as e:
            print(f"Error retrieving analysis result: {e}")
            return None

    def process_document(self, file_path: str, doc_type: str) -> str:
        try:
            if file_path.endswith('.pdf'):
                text = self._extract_pdf_text(file_path)
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            
            doc_hash = hashlib.md5(text.encode()).hexdigest()
            existing = self.collection.find_one({"doc_hash": doc_hash})
            if existing:
                return doc_hash
            
            chunks = self._chunk_text(text)
            embeddings = self.embedding_model.encode(chunks).tolist()
            
            documents = [
                {
                    "doc_hash": doc_hash,
                    "doc_type": doc_type,
                    "chunk_id": i,
                    "text": chunk,
                    "embedding": embedding,
                    "created_at": datetime.now()
                }
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
            ]
            
            self.collection.insert_many(documents)
            return doc_hash
            
        except Exception as e:
            print(f"Error processing document: {e}")
            return None
    
    def semantic_search(self, query: str, doc_hash: str, top_k: int = 3) -> List[str]:
        try:
            query = query[:1000]  # Truncate long queries
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
    
    def _chunk_text(self, text: str) -> List[str]:
        words = text.split()
        chunks = []
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk = ' '.join(words[i:i + self.chunk_size])
            if chunk.strip():
                chunks.append(chunk.strip())
        return chunks

# Initialize global components
rag_processor = RAGProcessor()
tavily_client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

def student_intent_analyzer_agent(state: CompatibilityState) -> CompatibilityState:
    print("🎯 Analyzing student intents...")
    
    if not state["resume_path"] or not state["career_goals"]:
        print("Missing required inputs for intent analysis")
        return {**state, "student_intents": {}}
    
    try:
        resume_hash = rag_processor.process_document(state["resume_path"], "resume")
        linkedin_text = ""
        if state["linkedin_path"]:
            with open(state["linkedin_path"], 'r', encoding='utf-8') as f:
                linkedin_text = f.read()
        
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

        {combined_context[:2000]}

        Return a JSON object with:
        {{
            "desired_industries": ["industry1", "industry2", ...],
            "preferred_culture": ["startup", "corporate", "remote-first", ...],
            "work_preferences": ["remote", "hybrid", "in-office", ...],
            "learning_goals": ["mentorship", "training", "certification", ...],
            "career_aspirations": ["leadership", "technical expertise", "entrepreneurship", ...]
        }}

        Rules:
        1. Base your response solely on the provided context.
        2. Do not infer information not explicitly stated.
        3. Ensure all values are arrays of strings.
        """
        
        response = gemini_model.generate_content(prompt)
        result_text = response.text.strip().replace('```json', '').replace('```', '')
        student_intents = json.loads(result_text)
        
        print(f"✅ Extracted intents: {len(student_intents.get('desired_industries', []))} industries")
        
    except Exception as e:
        print(f"Error in student intent analysis: {e}")
        student_intents = {
            "desired_industries": ["Technology"],
            "preferred_culture": ["Innovative"],
            "work_preferences": ["Hybrid"],
            "learning_goals": ["Skill Development"],
            "career_aspirations": ["Technical Leadership"]
        }
    
    return {**state, "student_intents": student_intents}

def company_culture_extractor_agent(state: CompatibilityState) -> CompatibilityState:
    print("🏢 Extracting company culture...")
    
    if not state["company_data_path"]:
        print("Missing company data path")
        return {**state, "company_culture": {}}
    
    try:
        company_hash = rag_processor.process_document(state["company_data_path"], "company")
        web_context = ""
        if state["company_urls"]:
            for url in state["company_urls"][:3]:
                try:
                    search_query = f"company culture values work life balance {url}"
                    search_results = tavily_client.search(search_query, max_results=3)
                    for result in search_results.get("results", []):
                        web_context += result.get("content", "") + " "
                except:
                    continue
        
        culture_queries = [
            "company values mission vision culture",
            "work life balance flexible working",
            "learning development training programs",
            "team collaboration communication style"
        ]
        
        combined_context = ""
        for query in culture_queries:
            relevant_chunks = rag_processor.semantic_search(query, company_hash, top_k=2)
            combined_context += " ".join(relevant_chunks) + " "
        
        combined_context += web_context + " " + state["job_descriptions"]
        
        prompt = f"""
        Analyze the following company information to extract cultural traits:

        {combined_context[:2000]}

        Return a JSON object with:
        {{
            "values": ["value1", "value2", ...],
            "work_life_balance": "description",
            "learning_support": ["program1", "program2", ...],
            "team_culture": "description",
            "company_size": "startup/medium/large"
        }}

        Rules:
        1. Base your response solely on the provided context.
        2. Do not infer information not explicitly stated.
        3. Ensure values and learning_support are arrays of strings.
        """
        
        response = gemini_model.generate_content(prompt)
        result_text = response.text.strip().replace('```json', '').replace('```', '')
        company_culture = json.loads(result_text)
        
        print(f"✅ Extracted culture: {len(company_culture.get('values', []))} values")
        
    except Exception as e:
        print(f"Error in company culture extraction: {e}")
        company_culture = {
            "values": ["Innovation"],
            "work_life_balance": "Flexible hours",
            "learning_support": ["Training"],
            "team_culture": "Collaborative",
            "company_size": "Medium"
        }
    
    return {**state, "company_culture": company_culture}

def skill_role_alignment_agent(state: CompatibilityState) -> CompatibilityState:
    print("🎯 Analyzing skill-role alignment...")
    
    if not state["resume_path"] or not state["job_descriptions"]:
        print("Missing required inputs for skill alignment")
        return {**state, "skill_alignment": {}}
    
    try:
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
        
        job_skills_prompt = f"""
        Extract technical skills from these job descriptions:

        {state["job_descriptions"][:1500]}

        Return a JSON array: ["skill1", "skill2", ...]
        Rules:
        1. Base your response solely on the provided context.
        2. Do not infer skills not explicitly stated.
        """
        
        job_skills_response = gemini_model.generate_content(job_skills_prompt)
        job_skills_text = job_skills_response.text.strip().replace('```json', '').replace('```', '')
        try:
            job_skills = json.loads(job_skills_text)
        except:
            job_skills = re.findall(r'"([^"]+)"', job_skills_text)
        
        alignment_prompt = f"""
        Analyze skill alignment:

        Student Context: {resume_skills_context[:1500]}
        Job Requirements: {state["job_descriptions"][:1500]}
        Required Skills: {job_skills}

        Return JSON with:
        {{
            "matched_skills": ["skill1", "skill2", ...],
            "skill_gaps": ["missing_skill1", "missing_skill2", ...],
            "hidden_opportunities": ["opportunity1", "opportunity2", ...],
            "transferable_skills": ["skill1", "skill2", ...]
        }}

        Rules:
        1. Base your response solely on the provided context.
        2. Identify at least one hidden opportunity.
        """
        
        response = gemini_model.generate_content(alignment_prompt)
        result_text = response.text.strip().replace('```json', '').replace('```', '')
        skill_alignment = json.loads(result_text)
        
        print(f"✅ Skill alignment: {len(skill_alignment.get('matched_skills', []))} matched")
        
    except Exception as e:
        print(f"Error in skill alignment: {e}")
        skill_alignment = {
            "matched_skills": ["Python"],
            "skill_gaps": ["Machine Learning"],
            "hidden_opportunities": ["Data Analysis"],
            "transferable_skills": ["Communication"]
        }
    
    return {**state, "skill_alignment": skill_alignment}

def fit_scorer_agent(state: CompatibilityState) -> CompatibilityState:
    print("📊 Calculating compatibility score...")
    
    if not state["student_intents"] or not state["company_culture"] or not state["skill_alignment"]:
        print("Missing required inputs for scoring")
        return {**state, "compatibility_score": {}}
    
    try:
        intent_score = calculate_intent_alignment(state["student_intents"], state["company_culture"])
        skill_score = calculate_skill_match(state["skill_alignment"])
        culture_score = calculate_cultural_fit(state["student_intents"], state["company_culture"])
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
            "overall_score": 60,
            "intent_alignment": 60,
            "skill_match": 60,
            "cultural_fit": 60,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "analysis_version": "1.0",
                "confidence": "medium"
            }
        }
    
    return {**state, "compatibility_score": compatibility_score}

def counselor_agent(state: CompatibilityState) -> CompatibilityState:
    print("🎓 Generating counseling report...")
    
    if not state["compatibility_score"]:
        print("Missing compatibility score")
        return {**state, "counseling_report": {}}
    
    try:
        score = state["compatibility_score"]["overall_score"]
        
        counseling_prompt = f"""
        Generate a counseling report:

        Overall Score: {score}%
        Student Intents: {state["student_intents"]}
        Company Culture: {state["company_culture"]}
        Skill Alignment: {state["skill_alignment"]}

        Return JSON with:
        {{
            "match_reasoning": "explanation",
            "alternative_suggestions": ["suggestion1", "suggestion2", ...],
            "actionable_advice": ["advice1", "advice2", ...],
            "skill_development_plan": ["step1", "step2", ...]
        }}

        Rules:
        1. Base your response solely on the provided context.
        2. For scores below 70, suggest at least 2 alternatives.
        3. Make advice specific and actionable.
        """
        
        response = gemini_model.generate_content(counseling_prompt)
        result_text = response.text.strip().replace('```json', '').replace('```', '')
        counseling_report = json.loads(result_text)
        
        print("✅ Counseling report generated")
        
    except Exception as e:
        print(f"Error in counseling: {e}")
        counseling_report = {
            "match_reasoning": "Moderate fit based on available data",
            "alternative_suggestions": ["Explore similar roles", "Consider other companies"],
            "actionable_advice": ["Develop technical skills", "Research company culture"],
            "skill_development_plan": ["Take online courses", "Build projects"]
        }
    
    return {**state, "counseling_report": counseling_report}

def calculate_intent_alignment(student_intents: Dict, company_culture: Dict) -> int:
    score = 0
    if any(industry.lower() in " ".join(company_culture.get("values", [])).lower() 
           for industry in student_intents.get("desired_industries", [])):
        score += 30
    student_culture = [c.lower() for c in student_intents.get("preferred_culture", [])]
    company_values = [v.lower() for v in company_culture.get("values", [])]
    if any(sc in " ".join(company_values) for sc in student_culture):
        score += 40
    if "remote" in student_intents.get("work_preferences", []) and \
       "flexible" in company_culture.get("work_life_balance", "").lower():
        score += 30
    return min(score, 100)

def calculate_skill_match(skill_alignment: Dict) -> int:
    matched = len(skill_alignment.get("matched_skills", []))
    gaps = len(skill_alignment.get("skill_gaps", []))
    if matched + gaps == 0:
        return 50
    return int((matched / (matched + gaps)) * 100)

def calculate_cultural_fit(student_intents: Dict, company_culture: Dict) -> int:
    score = 0
    student_learning = student_intents.get("learning_goals", [])
    company_learning = company_culture.get("learning_support", [])
    if any(sl.lower() in " ".join(company_learning).lower() for sl in student_learning):
        score += 50
    aspirations = student_intents.get("career_aspirations", [])
    company_values = company_culture.get("values", [])
    if any(asp.lower() in " ".join(company_values).lower() for asp in aspirations):
        score += 50
    return min(score, 100)

def build_compatibility_graph() -> StateGraph:
    graph_builder = StateGraph(CompatibilityState)
    
    graph_builder.add_node("student_intent_analyzer", student_intent_analyzer_agent)
    graph_builder.add_node("company_culture_extractor", company_culture_extractor_agent)
    graph_builder.add_node("skill_role_alignment", skill_role_alignment_agent)
    graph_builder.add_node("fit_scorer", fit_scorer_agent)
    graph_builder.add_node("counselor", counselor_agent)
    
    graph_builder.set_entry_point("student_intent_analyzer")
    graph_builder.add_edge("student_intent_analyzer", "company_culture_extractor")
    graph_builder.add_edge("company_culture_extractor", "skill_role_alignment")
    graph_builder.add_edge("skill_role_alignment", "fit_scorer")
    graph_builder.add_edge("fit_scorer", "counselor")
    graph_builder.add_edge("counselor", END)
    
    return graph_builder.compile()

class CompatibilityService:
    def __init__(self):
        self.graph = build_compatibility_graph()
    
    async def analyze_compatibility(self, request_data: Dict[str, Any]) -> str:
        """Analyze compatibility and return analysis ID"""
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
        
        # Prepare data for MongoDB storage
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
        
        # Save to MongoDB and get ID
        analysis_id = rag_processor.save_analysis_result(analysis_result)
        
        if not analysis_id:
            raise Exception("Failed to save analysis result to database")
        
        print("✅ Analysis completed and saved!")
        return analysis_id
    
    async def get_analysis_by_id(self, analysis_id: str) -> Dict[str, Any]:
        """Retrieve analysis result by ID"""
        print(f"🔍 Retrieving analysis for ID: {analysis_id}")
        
        result = rag_processor.get_analysis_result(analysis_id)
        
        if not result:
            raise ValueError(f"No analysis found for ID: {analysis_id}")
        
        return result