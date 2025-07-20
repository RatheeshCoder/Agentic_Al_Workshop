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
import faiss
from app.schemas.compatibility_schemas import *

from dotenv import load_dotenv
from app.database.connection import db

# Load environment variables from .env file
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

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
        # MongoDB for analysis results
        self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[db_name]
        self.results_collection = self.db.compatibility_results
        
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_dim = 384  
        self.index = faiss.IndexFlatL2(self.embedding_dim) 
        self.chunk_metadata = [] 
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def __del__(self):
        self.client.close()

    def save_analysis_result(self, analysis_data: Dict[str, Any]) -> str:
        """Save the complete analysis result to MongoDB and return the ID"""
        try:
            analysis_data["created_at"] = datetime.now()
            analysis_data["status"] = "completed"
            result = self.results_collection.insert_one(analysis_data)
            print(f"✅ Analysis result saved with ID: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            print(f"Error saving analysis result: {e}")
            return None
    
    def get_analysis_result(self, analysis_id: str) -> Dict[str, Any]:
        """Retrieve analysis result by ID"""
        try:
            object_id = ObjectId(analysis_id)
            result = self.results_collection.find_one({"_id": object_id})
            if result:
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
            
            # Check if document already exists
            if any(meta['doc_hash'] == doc_hash for meta in self.chunk_metadata):
                return doc_hash
            
            chunks = self._chunk_text(text)
            embeddings = self.embedding_model.encode(chunks).astype('float32')
            
            # Add embeddings to Faiss index
            self.index.add(embeddings)
            
            # Store metadata
            for i, chunk in enumerate(chunks):
                self.chunk_metadata.append({
                    "doc_hash": doc_hash,
                    "doc_type": doc_type,
                    "chunk_id": i,
                    "text": chunk,
                    "created_at": datetime.now()
                })
            
            return doc_hash
        except Exception as e:
            print(f"Error processing document: {e}")
            return None
    
    def semantic_search(self, query: str, doc_hash: str, top_k: int = 3) -> List[str]:
        try:
            query = query[:1000]  # Truncate long queries
            query_embedding = self.embedding_model.encode([query])[0].astype('float32').reshape(1, -1)
            
            # Filter chunks for specific document hash
            relevant_indices = [i for i, meta in enumerate(self.chunk_metadata) 
                              if meta['doc_hash'] == doc_hash]
            
            if not relevant_indices:
                return []
            
            # Get embeddings for relevant chunks
            relevant_embeddings = np.array([self.index.reconstruct(i) for i in relevant_indices])
            
            # Search within relevant embeddings
            distances, indices = self.index.search(query_embedding, min(top_k, len(relevant_indices)))
            
            results = []
            for idx in indices[0]:
                if idx < len(self.chunk_metadata):  # Ensure valid index
                    results.append(self.chunk_metadata[idx]["text"])
            
            return results[:top_k]
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
gemini_model = genai.GenerativeModel(
    "gemini-2.5-flash",
    generation_config=genai.types.GenerationConfig(temperature=0.7)
)

def clean_json_response(response_text: str) -> str:
    """Clean and extract JSON from Gemini response"""
    cleaned = response_text.strip()
    cleaned = re.sub(r'```json\s*', '', cleaned)
    cleaned = re.sub(r'```\s*', '', cleaned)
    start = cleaned.find('{')
    end = cleaned.rfind('}') + 1
    if start != -1 and end > start:
        return cleaned[start:end]
    return cleaned

def student_intent_analyzer_agent(state: CompatibilityState) -> CompatibilityState:
    print("🎯 Analyzing student intents...")
    
    if not state["resume_path"] or not state["career_goals"]:
        print("Missing required inputs for intent analysis")
        return {**state, "student_intents": {}}
    
    try:
        resume_hash = rag_processor.process_document(state["resume_path"], "resume")
        linkedin_text = ""
        if state["linkedin_path"]:
            try:
                with open(state["linkedin_path"], 'r', encoding='utf-8') as f:
                    linkedin_text = f.read()
            except:
                linkedin_text = ""
        
        queries = [
            "career goals aspirations future plans objectives",
            "preferred industries technology software development",
            "work environment culture preferences remote office hybrid",
            "learning development training mentorship goals growth",
            "company size startup corporate enterprise preferences",
            "role responsibilities leadership technical management",
            "values innovation collaboration teamwork independence"
        ]
        
        combined_context = ""
        for query in queries:
            relevant_chunks = rag_processor.semantic_search(query, resume_hash, top_k=2)
            combined_context += " ".join(relevant_chunks) + " "
        
        full_context = f"{combined_context} {linkedin_text} {state['career_goals']}"
        
        prompt = f"""
        Analyze the following information to extract detailed student intents and preferences:

        Context: {full_context[:3000]} 

        Extract and return a JSON object with the following structure:
        {{
            "desired_industries": ["Technology", "Software Development", "Web Development", "..."],
            "preferred_culture": ["innovative", "collaborative", "startup", "remote-first", "..."],
            "work_preferences": ["remote", "hybrid", "in-office", "flexible", "..."],
            "learning_goals": ["mentorship", "training", "certification", "skill development", "..."],
            "career_aspirations": ["technical leadership", "full-stack development", "team lead", "..."],
            "company_size_preference": ["startup", "medium", "large", "enterprise"],
            "role_preferences": ["individual contributor", "team lead", "technical architect", "..."],
            "values": ["innovation", "growth", "work-life balance", "collaboration", "..."]
        }}

        Guidelines:
        1. Extract information directly from the provided context
        2. Infer reasonable preferences based on the candidate's background and goals
        3. For software developers, include relevant technical aspirations
        4. If context is limited, provide reasonable defaults for a software professional
        5. Ensure all arrays contain at least one relevant item
        """
        
        response = gemini_model.generate_content(prompt)
        result_text = clean_json_response(response.text)
        
        try:
            student_intents = json.loads(result_text)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            student_intents = {
                "desired_industries": ["Technology", "Software Development"],
                "preferred_culture": ["innovative", "collaborative"],
                "work_preferences": ["hybrid", "flexible"],
                "learning_goals": ["skill development", "mentorship"],
                "career_aspirations": ["technical expertise", "full-stack development"],
                "company_size_preference": ["medium", "startup"],
                "role_preferences": ["individual contributor", "technical lead"],
                "values": ["innovation", "growth", "work-life balance"]
            }
        
        print(f"✅ Extracted intents: {len(student_intents.get('desired_industries', []))} industries")
        
    except Exception as e:
        print(f"Error in student intent analysis: {e}")
        student_intents = {
            "desired_industries": ["Technology", "Software Development"],
            "preferred_culture": ["innovative", "collaborative"],
            "work_preferences": ["hybrid", "flexible"],
            "learning_goals": ["skill development", "mentorship"],
            "career_aspirations": ["technical expertise"],
            "company_size_preference": ["medium"],
            "role_preferences": ["individual contributor"],
            "values": ["innovation", "growth"]
        }
    
    return {**state, "student_intents": student_intents}

def company_culture_extractor_agent(state: CompatibilityState) -> CompatibilityState:
    print("🏢 Extracting company culture...")
    
    if not state["company_data_path"] and not state["job_descriptions"]:
        print("Missing company data")
        return {**state, "company_culture": {}}
    
    try:
        company_context = ""
        if state["company_data_path"]:
            company_hash = rag_processor.process_document(state["company_data_path"], "company")
            culture_queries = [
                "company values mission vision culture",
                "work life balance flexible working remote",
                "learning development training programs mentorship",
                "team collaboration communication style",
                "innovation technology growth opportunities",
                "employee benefits compensation packages"
            ]
            
            for query in culture_queries:
                relevant_chunks = rag_processor.semantic_search(query, company_hash, top_k=2)
                company_context += " ".join(relevant_chunks) + " "
        
        web_context = ""
        if state["company_urls"]:
            urls = []
            for url_item in state["company_urls"]:
                if isinstance(url_item, str):
                    cleaned_url = url_item.strip('[]"\'')
                    if cleaned_url.startswith('http'):
                        urls.append(cleaned_url)
            
            for url in urls[:3]:
                try:
                    company_name = url.split('//')[-1].split('/')[0].replace('www.', '').split('.')[0]
                    search_query = f"{company_name} company culture values work environment"
                    search_results = tavily_client.search(search_query, max_results=2)
                    for result in search_results.get("results", []):
                        web_context += result.get("content", "")[:500] + " "
                except Exception as e:
                    print(f"Error searching for company info: {e}")
                    continue
        
        full_context = f"{company_context} {web_context} {state['job_descriptions']}"
        
        prompt = f"""
        Analyze the following company information to extract comprehensive cultural traits:

        Company Information: {full_context[:3000]}

        Extract and return a JSON object with:
        {{
            "values": ["innovation", "collaboration", "integrity", "customer focus", "..."],
            "work_life_balance": "detailed description of work-life balance policies",
            "learning_support": ["training programs", "mentorship", "conferences", "..."],
            "team_culture": "detailed description of team dynamics and culture",
            "company_size": "startup/small/mediumlarge/enterprise",
            "work_environment": ["remote-friendly", "hybrid", "office-based", "flexible", "..."],
            "growth_opportunities": ["career advancement", "skill development", "leadership", "..."],
            "benefits": ["health insurance", "flexible hours", "professional development", "..."],
            "technology_focus": ["cutting-edge", "established", "innovative", "..."],
            "leadership_style": ["collaborative", "hierarchical", "flat", "..."]
        }}

        Guidelines:
        1. Extract specific information from the provided context
        2. If information is limited, provide reasonable inferences
        3. Be specific about company culture aspects
        4. Ensure all arrays contain relevant items
        """
        
        response = gemini_model.generate_content(prompt)
        result_text = clean_json_response(response.text)
        
        try:
            company_culture = json.loads(result_text)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            company_culture = {
                "values": ["innovation", "collaboration", "excellence"],
                "work_life_balance": "Standard work-life balance policies",
                "learning_support": ["professional development", "training"],
                "team_culture": "Collaborative and professional environment",
                "company_size": "medium",
                "work_environment": ["office-based", "flexible"],
                "growth_opportunities": ["career advancement", "skill development"],
                "benefits": ["competitive compensation", "professional development"],
                "technology_focus": ["established", "innovative"],
                "leadership_style": ["collaborative"]
            }
        
        print(f"✅ Extracted culture: {len(company_culture.get('values', []))} values")
        
    except Exception as e:
        print(f"Error in company culture extraction: {e}")
        company_culture = {
            "values": ["innovation", "collaboration"],
            "work_life_balance": "Standard policies",
            "learning_support": ["training"],
            "team_culture": "Professional environment",
            "company_size": "medium",
            "work_environment": ["office-based"],
            "growth_opportunities": ["career advancement"],
            "benefits": ["competitive compensation"],
            "technology_focus": ["established"],
            "leadership_style": ["collaborative"]
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
            "programming languages python javascript java react",
            "frameworks libraries react angular vue node express",
            "databases mysql mongodb postgresql redis",
            "tools technologies git docker kubernetes aws",
            "soft skills communication leadership teamwork",
            "experience years projects internships freelancing",
            "methodologies agile scrum devops ci cd"
        ]
        
        resume_skills_context = ""
        for query in skill_queries:
            relevant_chunks = rag_processor.semantic_search(query, resume_hash, top_k=3)
            resume_skills_context += " ".join(relevant_chunks) + " "
        
        job_skills_prompt = f"""
        Analyze these job descriptions and extract ALL required and preferred skills:

        Job Descriptions: {state["job_descriptions"][:2000]}

        Return a JSON object with:
        {{
            "required_skills": ["skill1", "skill2", "..."],
            "preferred_skills": ["skill1", "skill2", "..."],
            "experience_level": "junior/mid/senior",
            "key_responsibilities": ["resp1", "resp2", "..."]
        }}

        Guidelines:
        1. Separate must-have skills from nice-to-have skills
        2. Include both technical and soft skills
        3. Extract specific technologies, frameworks, and tools mentioned
        """
        
        job_skills_response = gemini_model.generate_content(job_skills_prompt)
        job_skills_text = clean_json_response(job_skills_response.text)
        
        try:
            job_requirements = json.loads(job_skills_text)
        except json.JSONDecodeError:
            job_requirements = {
                "required_skills": re.findall(r'\b(?:React|JavaScript|TypeScript|Node|Python|Java|HTML|CSS|SQL)\b', state["job_descriptions"]),
                "preferred_skills": [],
                "experience_level": "mid",
                "key_responsibilities": ["Software Development"]
            }
        
        alignment_prompt = f"""
        Perform comprehensive skill alignment analysis:

        Student Context: {resume_skills_context[:2000]}
        Career Goals: {state["career_goals"]}
        Job Requirements: {json.dumps(job_requirements)}

        Analyze and return JSON with:
        {{
            "matched_skills": ["skill1", "skill2", "..."],
            "skill_gaps": ["missing_skill1", "missing_skill2", "..."],
            "transferable_skills": ["skill1", "skill2", "..."],
            "hidden_opportunities": ["opportunity1", "opportunity2", "..."],
            "experience_match": "junior/mid/senior",
            "skill_match_percentage": 85,
            "areas_for_improvement": ["area1", "area2", "..."],
            "unique_strengths": ["strength1", "strength2", "..."]
        }}

        Guidelines:
        1. Compare student skills against job requirements thoroughly
        2. Identify skills that transfer between domains
        3. Calculate realistic skill match percentage
        4. Identify unique strengths and improvement areas
        5. Consider both technical and soft skills
        """
        
        response = gemini_model.generate_content(alignment_prompt)
        result_text = clean_json_response(response.text)
        
        try:
            skill_alignment = json.loads(result_text)
            if "skill_match_percentage" not in skill_alignment:
                matched_count = len(skill_alignment.get("matched_skills", []))
                total_required = len(job_requirements.get("required_skills", [])) + len(job_requirements.get("preferred_skills", []))
                skill_alignment["skill_match_percentage"] = int((matched_count / max(total_required, 1)) * 100)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            matched_skills = []
            all_job_skills = job_requirements.get("required_skills", []) + job_requirements.get("preferred_skills", [])
            for skill in all_job_skills:
                if skill.lower() in resume_skills_context.lower():
                    matched_skills.append(skill)
            
            skill_gaps = [skill for skill in job_requirements.get("required_skills", []) if skill not in matched_skills]
            skill_match_percentage = int((len(matched_skills) / max(len(all_job_skills), 1)) * 100)
            
            skill_alignment = {
                "matched_skills": matched_skills,
                "skill_gaps": skill_gaps,
                "transferable_skills": ["Communication", "Problem Solving"],
                "hidden_opportunities": ["Full-stack development", "Leadership potential"],
                "experience_match": "mid",
                "skill_match_percentage": skill_match_percentage,
                "areas_for_improvement": skill_gaps[:3],
                "unique_strengths": ["Full-stack experience", "Client project delivery"]
            }
        
        print(f"✅ Skill alignment: {len(skill_alignment.get('matched_skills', []))} matched, {skill_alignment.get('skill_match_percentage', 0)}% match")
        
    except Exception as e:
        print(f"Error in skill alignment: {e}")
        skill_alignment = {
            "matched_skills": ["React", "JavaScript"],
            "skill_gaps": ["Advanced Redux", "Testing"],
            "transferable_skills": ["Communication", "Problem Solving"],
            "hidden_opportunities": ["Full-stack development"],
            "experience_match": "mid",
            "skill_match_percentage": 60,
            "areas_for_improvement": ["Testing", "Advanced State Management"],
            "unique_strengths": ["Full-stack experience"]
        }
    
    return {**state, "skill_alignment": skill_alignment}

def calculate_intent_alignment(student_intents: Dict, company_culture: Dict) -> int:
    score = 0
    max_score = 100
    
    student_industries = [ind.lower() for ind in student_intents.get("desired_industries", [])]
    company_values = [val.lower() for val in company_culture.get("values", [])]
    company_focus = company_culture.get("technology_focus", [])
    
    if any(industry in ["technology", "software", "tech"] for industry in student_industries):
        if any(tech in ["innovative", "cutting-edge", "technology"] for tech in company_focus):
            score += 25
        else:
            score += 15
    
    student_culture = [c.lower() for c in student_intents.get("preferred_culture", [])]
    if any(sc in " ".join(company_values) for sc in student_culture):
        score += 25
    
    student_work_prefs = [wp.lower() for wp in student_intents.get("work_preferences", [])]
    company_work_env = [we.lower() for we in company_culture.get("work_environment", [])]
    
    if any(swp in " ".join(company_work_env) for swp in student_work_prefs):
        score += 25
    elif "flexible" in student_work_prefs and "flexible" in company_culture.get("work_life_balance", "").lower():
        score += 20
    
    student_learning = [lg.lower() for lg in student_intents.get("learning_goals", [])]
    company_learning = [ls.lower() for ls in company_culture.get("learning_support", [])]
    
    if any(sl in " ".join(company_learning) for sl in student_learning):
        score += 25
    
    return min(score, max_score)

def calculate_skill_match(skill_alignment: Dict) -> int:
    return skill_alignment.get("skill_match_percentage", 0)

def calculate_cultural_fit(student_intents: Dict, company_culture: Dict) -> int:
    score = 0
    
    student_values = [val.lower() for val in student_intents.get("values", [])]
    company_values = [val.lower() for val in company_culture.get("values", [])]
    
    value_matches = sum(1 for sv in student_values if any(sv in cv for cv in company_values))
    if value_matches > 0:
        score += min(40, value_matches * 13)
    
    student_aspirations = [asp.lower() for asp in student_intents.get("career_aspirations", [])]
    company_growth = [go.lower() for go in company_culture.get("growth_opportunities", [])]
    
    if any(asp in " ".join(company_growth) for asp in student_aspirations):
        score += 30
    
    student_size_pref = student_intents.get("company_size_preference", [])
    company_size = company_culture.get("company_size", "medium")
    
    if company_size in [pref.lower() for pref in student_size_pref]:
        score += 30
    elif "medium" in [pref.lower() for pref in student_size_pref] and company_size in ["small", "medium", "large"]:
        score += 20
    
    return min(score, 100)

def fit_scorer_agent(state: CompatibilityState) -> CompatibilityState:
    print("📊 Calculating compatibility score...")
    
    if not state["student_intents"] or not state["company_culture"] or not state["skill_alignment"]:
        print("Missing required inputs for scoring")
        return {**state, "compatibility_score": {}}
    
    try:
        intent_score = calculate_intent_alignment(state["student_intents"], state["company_culture"])
        skill_score = calculate_skill_match(state["skill_alignment"])
        culture_score = calculate_cultural_fit(state["student_intents"], state["company_culture"])
        
        overall_score = int((skill_score * 0.4) + (intent_score * 0.3) + (culture_score * 0.3))
        
        compatibility_score = {
            "overall_score": overall_score,
            "intent_alignment": intent_score,
            "skill_match": skill_score,
            "cultural_fit": culture_score,
            "detailed_breakdown": {
                "technical_fit": skill_score,
                "career_alignment": intent_score,
                "cultural_alignment": culture_score,
                "experience_level_match": state["skill_alignment"].get("experience_match", "mid")
            },
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "analysis_version": "2.0",
                "confidence": "high" if overall_score > 75 else "medium" if overall_score > 50 else "low",
                "recommendation": "strong_match" if overall_score > 80 else "good_match" if overall_score > 65 else "potential_match" if overall_score > 45 else "poor_match"
            }
        }
        
        print(f"✅ Compatibility Score: {overall_score}% (Intent: {intent_score}%, Skill: {skill_score}%, Culture: {culture_score}%)")
        
    except Exception as e:
        print(f"Error in scoring: {e}")
        compatibility_score = {
            "overall_score": 60,
            "intent_alignment": 60,
            "skill_match": 60,
            "cultural_fit": 60,
            "detailed_breakdown": {
                "technical_fit": 60,
                "career_alignment": 60,
                "cultural_alignment": 60,
                "experience_level_match": "mid"
            },
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "analysis_version": "2.0",
                "confidence": "medium",
                "recommendation": "potential_match"
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
        
        analysis_id = rag_processor.save_analysis_result(analysis_result)
        
        if not analysis_id:
            raise Exception("Failed to save analysis result to database")
        
        print("✅ Analysis completed and saved!")
        return analysis_id
    
    async def get_analysis_by_id(self, analysis_id: str) -> Dict[str, Any]:
        print(f"🔍 Retrieving analysis for ID: {analysis_id}")
        
        result = rag_processor.get_analysis_result(analysis_id)
        
        if not result:
            raise ValueError(f"No analysis found for ID: {analysis_id}")
        
        return result