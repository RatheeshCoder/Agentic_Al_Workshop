import json
import re
from typing import Dict
from datetime import datetime
import google.generativeai as genai
from tavily import TavilyClient
from app.rag.rag_processor import RAGProcessor, CompatibilityState
from app.utils.clearJSON import clean_json_response
import os


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
            return {**state, "student_intents": {}}
        
        print(f"✅ Extracted intents: {len(student_intents.get('desired_industries', []))} industries")
        
    except Exception as e:
        print(f"Error in student intent analysis: {e}")
        return {**state, "student_intents": {}}
    
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
            "company_size": "startup/small/medium/large/enterprise",
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
            return {**state, "company_culture": {}}
        
        print(f"✅ Extracted culture: {len(company_culture.get('values', []))} values")
        
    except Exception as e:
        print(f"Error in company culture extraction: {e}")
        return {**state, "company_culture": {}}
    
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
            print("Failed to parse job requirements")
            return {**state, "skill_alignment": {}}
        
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
            return {**state, "skill_alignment": {}}
        
        print(f"✅ Skill alignment: {len(skill_alignment.get('matched_skills', []))} matched, {skill_alignment.get('skill_match_percentage', 0)}% match")
        
    except Exception as e:
        print(f"Error in skill alignment: {e}")
        return {**state, "skill_alignment": {}}
    
    return {**state, "skill_alignment": skill_alignment}

def fit_scorer_agent(state: CompatibilityState) -> CompatibilityState:
    print("📊 Calculating compatibility score...")
    
    if not state["student_intents"] or not state["company_culture"] or not state["skill_alignment"]:
        print("Missing required inputs for scoring")
        return {**state, "compatibility_score": {}}
    
    try:
        intent_score = calculate_intent_alignment_llm(state["student_intents"], state["company_culture"])
        skill_score = calculate_skill_match_llm(state["skill_alignment"])
        culture_score = calculate_cultural_fit_llm(state["student_intents"], state["company_culture"])
        
        # Use LLM to calculate overall score with better weighting logic
        overall_score = calculate_overall_score_llm(intent_score, skill_score, culture_score, state)
        
        compatibility_score = {
            "overall_score": overall_score,
            "intent_alignment": intent_score,
            "skill_match": skill_score,
            "cultural_fit": culture_score,
            "detailed_breakdown": {
                "technical_fit": skill_score,
                "career_alignment": intent_score,
                "cultural_alignment": culture_score,
                "experience_level_match": state["skill_alignment"].get("experience_match", "unknown")
            },
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "analysis_version": "2.0",
                "confidence": "high" if overall_score > 75 else "medium" if overall_score > 50 else "low",
                "recommendation": "strong_match" if overall_score > 80 else "good_match" if overall_score > 65 else "potential_match" if overall_score > 45 else "poor_match"
            }
        }
        
        print(f"✅ Compatibility Score: {overall_score}%")
        
    except Exception as e:
        print(f"Error in scoring: {e}")
        return {**state, "compatibility_score": {}}
    
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
        return {**state, "counseling_report": {}}
    
    return {**state, "counseling_report": counseling_report}

def calculate_intent_alignment_llm(student_intents: Dict, company_culture: Dict) -> int:
    """Use LLM to calculate intent alignment score"""
    try:
        prompt = f"""
        Analyze the alignment between student career intents and company culture.
        
        Student Intents: {json.dumps(student_intents)}
        Company Culture: {json.dumps(company_culture)}
        
        Calculate an intent alignment score (0-100) based on:
        1. How well the student's desired industries match the company's focus
        2. Alignment between preferred work culture and company values
        3. Match between work preferences (remote/hybrid/office) and company environment
        4. Compatibility of learning goals with company learning support
        5. Alignment of career aspirations with company growth opportunities
        
        Return only a JSON object with:
        {{
            "score": 85,
            "reasoning": "Brief explanation of the score",
            "key_alignments": ["alignment1", "alignment2"],
            "key_misalignments": ["misalignment1", "misalignment2"]
        }}
        
        Be analytical and consider both positive matches and potential conflicts.
        """
        
        response = gemini_model.generate_content(prompt)
        result_text = clean_json_response(response.text)
        result = json.loads(result_text)
        
        return result.get("score", 0)
        
    except Exception as e:
        print(f"Error in LLM intent alignment calculation: {e}")
        return 0

def calculate_skill_match_llm(skill_alignment: Dict) -> int:
    """Use LLM to calculate skill match score"""
    try:
        prompt = f"""
        Calculate a comprehensive skill match score based on the skill alignment analysis.
        
        Skill Alignment Data: {json.dumps(skill_alignment)}
        
        Consider:
        1. Number and importance of matched skills vs total required skills
        2. Severity and impact of skill gaps
        3. Value of transferable skills in the role context
        4. Experience level match (junior/mid/senior)
        5. Unique strengths that could compensate for gaps
        6. Hidden opportunities that add value
        
        Return only a JSON object with:
        {{
            "score": 78,
            "reasoning": "Brief explanation focusing on why this score",
            "strength_factors": ["factor1", "factor2"],
            "gap_impact": "high/medium/low impact of gaps"
        }}
        
        Be realistic - perfect matches are rare, but focus on overall employability.
        """
        
        response = gemini_model.generate_content(prompt)
        result_text = clean_json_response(response.text)
        result = json.loads(result_text)
        
        return result.get("score", 0)
        
    except Exception as e:
        print(f"Error in LLM skill match calculation: {e}")
        return 0

def calculate_cultural_fit_llm(student_intents: Dict, company_culture: Dict) -> int:
    """Use LLM to calculate cultural fit score"""
    try:
        prompt = f"""
        Evaluate the cultural fit between student and company.
        
        Student Intents: {json.dumps(student_intents)}
        Company Culture: {json.dumps(company_culture)}
        
        Analyze cultural compatibility across:
        1. Core values alignment (student values vs company values)
        2. Work style preferences vs company work environment
        3. Learning and development expectations vs company support
        4. Career growth aspirations vs company opportunities
        5. Team dynamics and leadership style preferences
        6. Work-life balance expectations vs company policies
        
        Return only a JSON object with:
        {{
            "score": 72,
            "reasoning": "Brief explanation of cultural compatibility",
            "cultural_matches": ["match1", "match2"],
            "potential_conflicts": ["conflict1", "conflict2"]
        }}
        
        Consider both explicit matches and implicit cultural signals.
        """
        
        response = gemini_model.generate_content(prompt)
        result_text = clean_json_response(response.text)
        result = json.loads(result_text)
        
        return result.get("score", 0)
        
    except Exception as e:
        print(f"Error in LLM cultural fit calculation: {e}")
        return 0

def calculate_overall_score_llm(intent_score: int, skill_score: int, culture_score: int, state: Dict) -> int:
    """Use LLM to calculate overall compatibility score with intelligent weighting"""
    try:
        prompt = f"""
        Calculate an overall compatibility score using intelligent weighting.
        
        Individual Scores:
        - Intent Alignment: {intent_score}%
        - Skill Match: {skill_score}%
        - Cultural Fit: {culture_score}%
        
        Additional Context:
        - Career Goals: {state.get("career_goals", "Not specified")}
        - Experience Level: {state.get("skill_alignment", {}).get("experience_match", "unknown")}
        - Job Role Type: Based on job descriptions and requirements
        
        Consider:
        1. For technical roles, skill match might be weighted higher
        2. For leadership roles, cultural fit and intent alignment are crucial
        3. Entry-level positions might prioritize cultural fit and learning intent
        4. Senior positions might emphasize skill match and experience alignment
        5. The overall narrative and coherence of the match
        
        Return only a JSON object with:
        {{
            "overall_score": 76,
            "weighting_rationale": "Brief explanation of weighting logic used",
            "recommendation_level": "strong_match/good_match/potential_match/poor_match"
        }}
        
        The score should reflect realistic hiring probability and mutual satisfaction.
        """
        
        response = gemini_model.generate_content(prompt)
        result_text = clean_json_response(response.text)
        result = json.loads(result_text)
        
        return result.get("overall_score", 0)
        
    except Exception as e:
        print(f"Error in LLM overall score calculation: {e}")
        return 0