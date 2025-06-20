import os
import json
import re
from typing import Dict, Any
import PyPDF2
from app.state_types import AgentState
from app.rag.rag_resume_processor import RAGResumeProcessor
import google.generativeai as genai

genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

rag_processor = RAGResumeProcessor()

def extract_text_from_pdf(pdf_path: str) -> str:
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            return "\n".join(page.extract_text() for page in reader.pages)
    except Exception as e:
        print(f"[PDF ERROR] {e}")
        return ""

def fallback_extraction(text: str) -> Dict[str, Any]:
    try:
        prompt = f"""
        Extract from this resume text:

        {text[:2000]}

        Return JSON:
        {{
          "skills": ["skill1", "skill2"],
          "education": "education summary",
          "experience": "experience summary",
          "projects": "project summary"
        }}
        """
        response = gemini_model.generate_content(prompt)
        return json.loads(response.text.strip())
    except:
        return {
            "skills": ["Python", "JavaScript"],
            "education": "Bachelor in Computer Science",
            "experience": "Internship experience",
            "projects": "Portfolio and academic projects"
        }

def extract_student_info_with_rag(pdf_hash: str) -> Dict[str, Any]:
    search_queries = {
        "skills": "technical skills programming languages frameworks tools",
        "education": "education degree university college academic",
        "experience": "work experience jobs internship roles",
        "projects": "projects portfolio built implemented"
    }

    info = {}

    for key, query in search_queries.items():
        chunks = rag_processor.semantic_search(query, pdf_hash, top_k=3)
        if not chunks:
            info[key] = [] if key == "skills" else "Not specified"
            continue

        combined = "\n".join([chunk["chunk"]["text"] for chunk in chunks])

        prompt = ""
        if key == "skills":
            prompt = f"Extract all technical skills as a JSON list from:\n\n{combined}"
        elif key == "education":
            prompt = f"Summarize education in 1-2 lines:\n\n{combined}"
        elif key == "experience":
            prompt = f"Summarize work experience in 2-3 lines:\n\n{combined}"
        elif key == "projects":
            prompt = f"Summarize projects in 2-3 lines:\n\n{combined}"

        response = gemini_model.generate_content(prompt)

        if key == "skills":
            try:
                skills_text = response.text.strip()
                if skills_text.startswith('```json'):
                    skills_text = skills_text.replace('```json', '').replace('```', '').strip()
                elif skills_text.startswith('```'):
                    skills_text = skills_text.replace('```', '').strip()

                info[key] = json.loads(skills_text)
            except:
                fallback = re.findall(r'"([^"]+)"', response.text)
                info[key] = fallback if fallback else response.text.split(",")[:20]
        else:
            info[key] = response.text.strip()[:300]

    return info

def pdf_extraction_agent(state: AgentState) -> AgentState:
    print("🧠 Agent 1: Resume Extraction using RAG...")

    pdf_text = extract_text_from_pdf(state["pdf_path"])

    if not pdf_text:
        info = fallback_extraction("")
    else:
        pdf_hash = rag_processor.process_and_store_resume(state["pdf_path"], pdf_text)
        info = extract_student_info_with_rag(pdf_hash) if pdf_hash else fallback_extraction(pdf_text)

    print(f"✅ Skills Found: {len(info['skills'])} → {info['skills'][:5]}")

    return {
        **state,
        "student_skills": info["skills"],
        "student_education": info["education"],
        "student_experience": info["experience"],
        "student_projects": info["projects"],
    }
