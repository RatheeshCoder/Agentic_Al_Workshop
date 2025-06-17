import streamlit as st
import os
import PyPDF2
import google.generativeai as genai
from tavily import TavilyClient
from dataclasses import dataclass
from typing import List
from langgraph.graph import StateGraph, END
import re
import io

# Page configuration
st.set_page_config(
    page_title="Student Readiness Evaluator",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    .skill-tag {
        display: inline-block;
        background: #e3f2fd;
        color: #1565c0;
        padding: 0.25rem 0.5rem;
        margin: 0.125rem;
        border-radius: 12px;
        font-size: 0.8rem;
    }
    .missing-skill-tag {
        display: inline-block;
        background: #ffebee;
        color: #c62828;
        padding: 0.25rem 0.5rem;
        margin: 0.125rem;
        border-radius: 12px;
        font-size: 0.8rem;
    }
    .recommendation-card {
        background: #f1f8e9;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #4caf50;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = None

@dataclass
class SearchResult:
    title: str
    content: str
    url: str

@dataclass
class GraphState:
    pdf_path: str
    academic_signals: str
    parsed_info: dict
    search_results: list
    industry_gap_summary: str
    alignment_score: float
    missing_skills: list
    upskilling_recommendations: dict
    target_role: str

def setup_apis():
    """Setup API keys and clients"""
    try:
        google_api_key = "Your_Google_API_Key_Here"
        tavily_api_key = "Your_Tavily_API_Key_Here"
        
        print(f"Google API Key: {google_api_key}")
        print(f"Tavily API Key: {tavily_api_key}")
        if not google_api_key or not tavily_api_key:
            st.error("⚠️ API keys not found. Please set GOOGLE_API_KEY and TAVILY_API_KEY in your environment or secrets.")
            return None, None
            
        genai.configure(api_key=google_api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        tavily = TavilyClient(api_key=tavily_api_key)
        
        return model, tavily
    except Exception as e:
        st.error(f"Error setting up APIs: {e}")
        return None, None

def extract_text_from_pdf(uploaded_file) -> str:
    """Extract text from uploaded PDF file"""
    try:
        uploaded_file.seek(0)
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return ""

def extract_academic_info(academic_text: str) -> dict:
    """Dynamically extract skills, projects, and education info from resume text"""
    skill_keywords = [
        "React", "Node", "MongoDB", "Express", "JavaScript", "Python", "AI",
        "Machine Learning", "HTML", "CSS", "SCSS", "PHP", "MySQL", "Tailwind",
        "WordPress", "Git", "GitHub", "Flask", "Next.js", "Bootstrap", "Agile",
        "TypeScript", "Vue", "Angular", "Docker", "Kubernetes", "AWS", "Azure",
        "Java", "C++", "C#", "Ruby", "Go", "Rust", "Swift", "Kotlin", "Dart",
        "Flutter", "React Native", "Firebase", "PostgreSQL", "Redis", "GraphQL",
        "REST API", "Microservices", "Linux", "Jenkins", "Terraform", "Django"
    ]

    # Case-insensitive skill matching
    skills = []
    text_lower = academic_text.lower()
    for skill in skill_keywords:
        if skill.lower() in text_lower:
            skills.append(skill)
    
    skills = sorted(set(skills))

    project_match = re.search(
        r"(Projects?|Major Projects?|Academic Projects?)\s*[:,\-]?\s*(.*?)(Education|Skills|Certification|Experience|Contact|$)", 
        academic_text, 
        re.IGNORECASE | re.DOTALL
    )
    projects = project_match.group(2).strip() if project_match else ""

    education_match = re.search(
        r"(Education|Academic Background|Qualification)\s*[:,\-]?\s*(.*?)(Projects|Skills|Certification|Experience|Contact|$)", 
        academic_text, 
        re.IGNORECASE | re.DOTALL
    )
    education = education_match.group(2).strip() if education_match else ""

    return {
        "skills": skills,
        "projects": projects.replace("\n", " ")[:500],  
        "education": education.replace("\n", " ")[:300]  
    }

def get_industry_needs(tavily, query: str, num_results: int = 5) -> List[SearchResult]:
    """Fetch industry needs using Tavily search with error handling"""
    try:
        results = tavily.search(
            query, 
            search_depth="basic", 
            max_results=num_results,
            include_answer=False,
            include_raw_content=False
        )
        
        search_results = []
        if results and "results" in results:
            for doc in results["results"]:
                search_results.append(SearchResult(
                    title=doc.get("title", "No Title"),
                    content=doc.get("content", "No Content")[:1000], 
                    url=doc.get("url", "")
                ))
        
        return search_results
    except Exception as e:
        st.error(f"Error fetching search results: {str(e)}")
        return [
            SearchResult(
                title=f"Sample Job Requirements for {query.split()[0]}",
                content=f"Key skills required include programming languages, frameworks, and problem-solving abilities relevant to {query}.",
                url="https://example.com"
            )
        ]

def summarize_industry_demands(model, question: str, search_results: List[SearchResult]) -> str:
    """Summarize industry demands using Gemini with better error handling"""
    try:
        if not search_results:
            return "No search results available for analysis."
        
        context = f"Question: {question}\n\nIndustry Information:\n"
        for i, result in enumerate(search_results[:3], 1): 
            context += f"{i}. {result.title}\n{result.content[:500]}...\n\n"

        prompt = context + """
        Based on the above information, summarize the key technical skills, qualifications, 
        and requirements mentioned for this role. Focus on:
        1. Programming languages and frameworks
        2. Tools and technologies
        3. Experience requirements
        4. Soft skills
        Keep the summary concise and actionable.
        """

        response = model.generate_content(prompt)
        return response.text.strip() if response.text else "Unable to generate summary."
    except Exception as e:
        st.warning(f"Error generating summary: {str(e)}")
        return f"Analysis based on {len(search_results)} job listings shows demand for technical skills, programming expertise, and relevant experience."

def get_missing_skills(student_skills: List[str], industry_summary: str) -> List[str]:
    """Extract missing skills from industry summary"""
    trending_skills = [
        "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Terraform", "Jenkins",
        "GraphQL", "Microservices", "Redis", "Elasticsearch", "Apache Kafka",
        "React", "Vue.js", "Angular", "Node.js", "Express", "Django", "Flask",
        "Spring Boot", "Laravel", "Ruby on Rails", "ASP.NET", "FastAPI",
        "MongoDB", "PostgreSQL", "MySQL", "SQLite", "Firebase", "Supabase",
        "Git", "GitHub", "GitLab", "CI/CD", "Agile", "Scrum", "DevOps",
        "Machine Learning", "TensorFlow", "PyTorch", "Scikit-learn", "Pandas",
        "NumPy", "Matplotlib", "Seaborn", "Jupyter", "VS Code", "IntelliJ"
    ]
    
    student_skills_lower = [skill.lower() for skill in student_skills]
    missing_skills = []
    
    for skill in trending_skills:
        if skill.lower() not in student_skills_lower:
            if skill.lower() in industry_summary.lower():
                missing_skills.append(skill)
    
    return missing_skills[:15]  

def run_analysis(uploaded_file, target_role, model, tavily):
    """Run the complete analysis pipeline with better error handling"""
    
    with st.spinner("🔍 Extracting information from resume..."):
        try:
            pdf_text = extract_text_from_pdf(uploaded_file)
            if not pdf_text:
                st.error("Could not extract text from PDF. Please ensure the PDF contains readable text.")
                return None
                
            parsed_info = extract_academic_info(pdf_text)
            st.success("✅ Resume information extracted successfully!")
        except Exception as e:
            st.error(f"Error extracting resume information: {str(e)}")
            return None
    
    with st.spinner("🌐 Fetching current industry requirements..."):
        try:
            query = f"{target_role} job requirements skills 2024 2025 hiring"
            search_results = get_industry_needs(tavily, query)
            st.success(f"✅ Found {len(search_results)} relevant sources!")
        except Exception as e:
            st.error(f"Error fetching industry data: {str(e)}")
            return None
    
    with st.spinner("🧠 Analyzing industry trends and requirements..."):
        try:
            industry_summary = summarize_industry_demands(
                model,
                f"What are the key skills and requirements for {target_role}?",
                search_results
            )
            st.success("✅ Industry analysis completed!")
        except Exception as e:
            st.error(f"Error analyzing industry trends: {str(e)}")
            return None
    
    with st.spinner("📊 Calculating alignment score..."):
        try:
            student_skills = parsed_info.get("skills", [])
            
            if not student_skills:
                alignment_score = 0
                matched_skills = []
            else:
                industry_summary_lower = industry_summary.lower()
                matched_skills = [skill for skill in student_skills if skill.lower() in industry_summary_lower]
                alignment_score = int((len(matched_skills) / len(student_skills)) * 100) if student_skills else 0
            
            st.success("✅ Alignment score calculated!")
        except Exception as e:
            st.error(f"Error calculating alignment: {str(e)}")
            return None
    
    with st.spinner("🎯 Generating upskilling recommendations..."):
        try:
            missing_skills = get_missing_skills(student_skills, industry_summary)
            
            recommendations = {
                "final_semester_electives": [
                    f"Advanced {skill} Development" for skill in missing_skills[:3]
                ] if missing_skills else ["Data Structures and Algorithms", "Software Engineering", "Database Systems"],
                "online_courses": [
                    f"Master {skill}" for skill in missing_skills[:5]
                ] if missing_skills else ["Full Stack Development", "Cloud Computing", "DevOps Fundamentals"],
                "project_suggestions": [
                    f"Build a {target_role.lower()} project using {skill}" for skill in missing_skills[:3]
                ] if missing_skills else [f"Portfolio website", f"{target_role} application", "Open source contribution"]
            }
            
            st.success("✅ Recommendations generated!")
        except Exception as e:
            st.error(f"Error generating recommendations: {str(e)}")
            return None
    
    return {
        "parsed_info": parsed_info,
        "search_results": search_results,
        "industry_summary": industry_summary,
        "alignment_score": alignment_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "recommendations": recommendations,
        "target_role": target_role
    }

def display_results(results):
    """Display analysis results in a formatted way"""
    
    st.markdown("""
    <div class="main-header">
        <h1>🎓 Student Readiness Analysis Report</h1>
        <p>Comprehensive evaluation of your readiness for the industry</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("👤 Student Profile")
        
        parsed = results["parsed_info"]
        
        st.markdown("**🎯 Target Role:**")
        st.info(results["target_role"])
        
        st.markdown("**💼 Skills:**")
        if parsed["skills"]:
            skills_html = "".join([f'<span class="skill-tag">{skill}</span>' for skill in parsed["skills"]])
            st.markdown(skills_html, unsafe_allow_html=True)
        else:
            st.warning("No technical skills detected in resume")
        
        st.markdown("**🎓 Education:**")
        st.text(parsed["education"] if parsed["education"] else "Education information not found")
        
        st.markdown("**🚀 Projects:**")
        st.text(parsed["projects"] if parsed["projects"] else "Project information not found")
    
    with col2:
        st.subheader("📊 Readiness Score")
        
        score = results["alignment_score"]
        if score >= 75:
            score_color = "green"
            status = "Excellent"
            emoji = "🎉"
        elif score >= 50:
            score_color = "orange"
            status = "Good"
            emoji = "👍"
        else:
            score_color = "red"
            status = "Needs Improvement"
            emoji = "📈"
        
        st.markdown(f"""
        <div style="text-align: center; padding: 2rem; background: #f8f9fa; border-radius: 10px;">
            <h1 style="color: {score_color}; margin: 0;">{score}%</h1>
            <h3 style="margin: 0.5rem 0;">{emoji} {status}</h3>
            <p style="color: #666;">Industry Alignment Score</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.subheader("✅ Matched Skills")
        if results["matched_skills"]:
            for skill in results["matched_skills"]:
                st.success(f"✓ {skill}")
        else:
            st.warning("No direct skill matches found")
    
    st.subheader("🏭 Industry Analysis Summary")
    with st.expander("View detailed industry requirements", expanded=False):
        st.markdown(results["industry_summary"])
    
    if results["missing_skills"]:
        st.subheader("❌ Skills Gap Analysis")
        st.markdown("**Top missing skills in demand:**")
        missing_skills_html = "".join([f'<span class="missing-skill-tag">{skill}</span>' for skill in results["missing_skills"][:10]])
        st.markdown(missing_skills_html, unsafe_allow_html=True)
    
    st.subheader("🎯 Upskilling Recommendations")
    
    rec_col1, rec_col2, rec_col3 = st.columns(3)
    
    with rec_col1:
        st.markdown("**📚 Recommended Electives**")
        for elective in results["recommendations"]["final_semester_electives"]:
            st.markdown(f"• {elective}")
    
    with rec_col2:
        st.markdown("**💻 Online Courses**")
        for course in results["recommendations"]["online_courses"]:
            st.markdown(f"• {course}")
    
    with rec_col3:
        st.markdown("**🚀 Project Ideas**")
        for project in results["recommendations"]["project_suggestions"]:
            st.markdown(f"• {project}")
    
    st.subheader("💼 Related Sources")
    with st.expander("View sources used in analysis"):
        for i, result in enumerate(results["search_results"][:5], 1):
            st.markdown(f"**{i}. {result.title}**")
            if result.url and result.url != "https://example.com":
                st.markdown(f"🔗 [{result.url}]({result.url})")
            st.markdown(f"_{result.content[:200]}..._")
            st.markdown("---")

def main():
    """Main Streamlit application"""
    
    st.title("🎓 Student Readiness Evaluator")
    st.markdown("**Analyze your academic preparation against current industry demands**")
    
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        model, tavily = setup_apis()
        
        if model and tavily:
            st.success("✅ APIs connected successfully")
        else:
            st.error("❌ API connection failed")
            st.stop()
        
        target_role = st.selectbox(
            "🎯 Select Target Role:",
            [
                "Full Stack Developer",
                "Frontend Developer", 
                "Backend Developer",
                "Data Scientist",
                "Machine Learning Engineer",
                "DevOps Engineer",
                "Mobile App Developer",
                "UI/UX Designer",
                "Product Manager",
                "Software Engineer"
            ]
        )
        
        st.markdown("---")
        st.markdown("**📋 Instructions:**")
        st.markdown("1. Upload your resume (PDF)")
        st.markdown("2. Select your target role")
        st.markdown("3. Click 'Analyze' to start")
        st.markdown("4. Review your readiness report")
    
    if not st.session_state.analysis_complete:
        st.markdown("### 📄 Upload Your Resume")
        
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type="pdf",
            help="Upload your resume in PDF format for analysis"
        )
        
        if uploaded_file is not None:
            st.success(f"✅ File uploaded: {uploaded_file.name}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"📄 **File:** {uploaded_file.name}")
            with col2:
                st.info(f"📊 **Size:** {uploaded_file.size / 1024:.1f} KB")
            
            st.markdown("---")
            
            if st.button("🚀 Start Analysis", type="primary", use_container_width=True):
                try:
                    results = run_analysis(uploaded_file, target_role, model, tavily)
                    if results:
                        st.session_state.analysis_results = results
                        st.session_state.analysis_complete = True
                        st.rerun()
                    else:
                        st.error("❌ Analysis failed. Please try again.")
                except Exception as e:
                    st.error(f"❌ Analysis failed: {str(e)}")
        else:
            st.info("👆 Please upload a PDF resume to get started")
    
    else:
        display_results(st.session_state.analysis_results)
        
        if st.button("🔄 Analyze Another Resume", type="secondary"):
            st.session_state.analysis_complete = False
            st.session_state.analysis_results = None
            st.rerun()

if __name__ == "__main__":
    main()