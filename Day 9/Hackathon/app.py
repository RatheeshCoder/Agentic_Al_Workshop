import os
import PyPDF2
import google.generativeai as genai
from tavily import TavilyClient
from dataclasses import dataclass
from typing import List, Dict, Any
from langgraph.graph import StateGraph, END
import chromadb
from chromadb.config import Settings
import numpy as np
from sentence_transformers import SentenceTransformer
import json
import hashlib
from datetime import datetime
import re

# Configuration
os.environ["GOOGLE_API_KEY"] = "your_google_key"
os.environ["TAVILY_API_KEY"] = "your_tavily_key"

# Vector Database Configuration
VECTOR_DB_PATH = "./vector_db"
COLLECTION_NAME = "industry_knowledge"

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF with better error handling"""
    if not pdf_path:
        print("❌ No PDF path provided")
        return ""
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        print(f"Current directory: {os.getcwd()}")
        print(f"Files in current directory: {os.listdir('.')}")
        return ""
    
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            
            if len(pdf_reader.pages) == 0:
                print("❌ PDF has no pages")
                return ""
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                except Exception as e:
                    print(f"⚠️ Error reading page {page_num + 1}: {e}")
                    continue
                    
        if not text.strip():
            print("❌ No text extracted from PDF")
            return ""
            
        print(f"✅ Successfully extracted {len(text)} characters from PDF")
        return text.strip()
        
    except Exception as e:
        print(f"❌ Error reading PDF: {e}")
        return ""

@dataclass
class SearchResult:
    title: str
    content: str
    url: str
    timestamp: str = ""
    relevance_score: float = 0.0

@dataclass
class ResearchQuestion:
    question: str
    search_results: List[SearchResult]
    summary: str = ""

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
    vector_db_results: list

class VectorRAG:
    """RAG implementation with vector database and embeddings"""
    
    def __init__(self, db_path: str = VECTOR_DB_PATH, collection_name: str = COLLECTION_NAME):
        self.db_path = db_path
        self.collection_name = collection_name
        self.embedding_model = None
        self.chroma_client = None
        self.collection = None
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize embedding model and vector database"""
        try:
            # Initialize embedding model
            print("🔧 Initializing embedding model...")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("✅ Embedding model loaded")
            
            # Initialize ChromaDB
            print("🔧 Initializing ChromaDB...")
            self.chroma_client = chromadb.PersistentClient(
                path=self.db_path,
                settings=Settings(allow_reset=True)
            )
            
            # Get or create collection
            try:
                self.collection = self.chroma_client.get_collection(name=self.collection_name)
                print(f"✅ Connected to existing collection: {self.collection_name}")
            except:
                self.collection = self.chroma_client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Industry knowledge and job requirements"}
                )
                print(f"✅ Created new collection: {self.collection_name}")
                
        except Exception as e:
            print(f"❌ Error initializing RAG components: {e}")
            raise
    
    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into overlapping chunks"""
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk.strip())
        
        return chunks
    
    def _generate_document_id(self, content: str, url: str = "") -> str:
        """Generate unique document ID based on content hash"""
        content_hash = hashlib.md5((content + url).encode()).hexdigest()
        return f"doc_{content_hash[:12]}"
    
    def store_documents(self, search_results: List[SearchResult]) -> None:
        """Store search results in vector database with embeddings"""
        print(f"💾 Storing {len(search_results)} documents in vector DB...")
        
        documents = []
        metadatas = []
        ids = []
        
        for result in search_results:
            # Chunk the content
            chunks = self._chunk_text(result.content)
            
            for i, chunk in enumerate(chunks):
                doc_id = f"{self._generate_document_id(result.content, result.url)}_chunk_{i}"
                
                # Check if document already exists
                try:
                    existing = self.collection.get(ids=[doc_id])
                    if existing['ids']:
                        continue  # Skip if already exists
                except:
                    pass
                
                documents.append(chunk)
                metadatas.append({
                    "title": result.title,
                    "url": result.url,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "timestamp": datetime.now().isoformat(),
                    "relevance_score": result.relevance_score
                })
                ids.append(doc_id)
        
        if documents:
            # Generate embeddings
            print(f"🔮 Generating embeddings for {len(documents)} chunks...")
            embeddings = self.embedding_model.encode(documents).tolist()
            
            # Store in ChromaDB
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
                ids=ids
            )
            print(f"✅ Stored {len(documents)} document chunks in vector DB")
        else:
            print("ℹ️ No new documents to store")
    
    def retrieve_relevant_docs(self, query: str, n_results: int = 10) -> List[Dict[str, Any]]:
        """Retrieve most relevant documents using vector similarity"""
        print(f"🔍 Retrieving relevant docs for: {query[:50]}...")
        
        try:
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query]).tolist()[0]
            
            # Search in vector DB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            retrieved_docs = []
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )):
                retrieved_docs.append({
                    "content": doc,
                    "metadata": metadata,
                    "similarity_score": 1 - distance,  # Convert distance to similarity
                    "rank": i + 1
                })
            
            print(f"✅ Retrieved {len(retrieved_docs)} relevant documents")
            return retrieved_docs
            
        except Exception as e:
            print(f"❌ Error retrieving documents: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector database collection"""
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection_name,
                "last_updated": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"❌ Error getting collection stats: {e}")
            return {"error": str(e)}

def initialize_clients():
    """Initialize API clients with error handling"""
    try:
        tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
        model = genai.GenerativeModel("gemini-1.5-flash")
        vector_rag = VectorRAG()
        return tavily, model, vector_rag
    except Exception as e:
        print(f"❌ Error initializing clients: {e}")
        return None, None, None

tavily, model, vector_rag = initialize_clients()

def get_industry_needs(query: str, num_results: int = 10) -> List[SearchResult]:
    """Fetch industry needs with better error handling"""
    if not tavily:
        print("❌ Tavily client not initialized")
        return []
        
    try:
        print(f"🔍 Searching: {query}")
        results = tavily.search(query, search_depth="advanced", max_results=num_results)
        
        search_results = []
        for doc in results.get("results", []):
            search_results.append(SearchResult(
                title=doc.get("title", "No title"),
                content=doc.get("content", "No content"),
                url=doc.get("url", "No URL"),
                timestamp=datetime.now().isoformat(),
                relevance_score=doc.get("score", 0.0)
            ))
        
        print(f"✅ Found {len(search_results)} results")
        return search_results
        
    except Exception as e:
        print(f"❌ Error fetching Tavily results: {e}")
        return []

def enhanced_summarize_with_rag(question: str, retrieved_docs: List[Dict[str, Any]]) -> str:
    """Enhanced summarization using RAG-retrieved documents"""
    if not model:
        return "❌ Gemini model not initialized"
        
    if not retrieved_docs:
        return "❌ No relevant documents found in vector database"
    
    # Prepare context from retrieved documents
    context = f"Question: {question}\n\nRelevant Information:\n\n"
    
    for i, doc in enumerate(retrieved_docs[:5], 1):  # Use top 5 most relevant
        context += f"Document {i} (Similarity: {doc['similarity_score']:.3f}):\n"
        context += f"Title: {doc['metadata'].get('title', 'Unknown')}\n"
        context += f"Content: {doc['content']}\n"
        context += f"Source: {doc['metadata'].get('url', 'Unknown')}\n\n"

    prompt = f"""{context}

Based on the above relevant documents, provide a comprehensive analysis that includes:

1. Key technical skills and competencies required
2. Industry trends and emerging technologies
3. Experience levels and qualifications expected
4. Specific tools, frameworks, and technologies mentioned
5. Soft skills and additional requirements

Focus on actionable insights that can help identify skill gaps and upskilling opportunities.
"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"❌ Failed to generate enhanced summary: {e}"

def extract_academic_info(academic_text: str) -> dict:
    """Dynamically extract skills, projects, and education info from a resume-like string."""
    if not academic_text:
        print("⚠️ No academic text provided")
        return {"skills": [], "projects": "", "education": "", "experience": ""}
    
    skill_keywords = [
        "React", "Node", "MongoDB", "Express", "JavaScript", "Python", "AI",
        "Machine Learning", "HTML", "CSS", "SCSS", "PHP", "MySQL", "Tailwind",
        "WordPress", "Git", "GitHub", "Flask", "Next.js", "Bootstrap", "Agile",
        "Docker", "Kubernetes", "AWS", "Azure", "TypeScript", "Vue", "Angular",
        "PostgreSQL", "Redis", "GraphQL", "Microservices", "DevOps", "CI/CD",
        "Testing", "Security", "Django", "Spring", "Java", "C++", "Go",
        "Rust", "Swift", "Kotlin", "TensorFlow", "PyTorch", "Scikit-learn"
    ]

    skills = sorted(set([kw for kw in skill_keywords if kw.lower() in academic_text.lower()]))

    # Extract projects
    project_match = re.search(r"(Projects?|Major Projects?)\s*[:,\-]?\s*(.*?)(Education|Skills|Certification|Experience|$)", academic_text, re.IGNORECASE | re.DOTALL)
    projects = project_match.group(2).strip() if project_match else ""

    # Extract education
    education_match = re.search(r"Education\s*[:,\-]?\s*(.*?)(Projects|Skills|Certification|Experience|$)", academic_text, re.IGNORECASE | re.DOTALL)
    education = education_match.group(1).strip() if education_match else ""

    # Extract experience
    experience_match = re.search(r"Experience\s*[:,\-]?\s*(.*?)(Projects|Skills|Certification|Education|$)", academic_text, re.IGNORECASE | re.DOTALL)
    experience = experience_match.group(1).strip() if experience_match else ""

    return {
        "skills": skills,
        "projects": projects.replace("\n", " ")[:500],
        "education": education.replace("\n", " ")[:500],
        "experience": experience.replace("\n", " ")[:500]
    }

def academic_signal_extraction(state):
    """Extract academic information from PDF"""
    print("\n📘 Extracting Academic Information...")
    
    pdf_text = extract_text_from_pdf(state["pdf_path"])
    if not pdf_text:
        print("❌ No text extracted from PDF. Using sample data.")
        pdf_text = """
        Education: Bachelor of Computer Science, XYZ University
        Skills: Python, JavaScript, React, Node.js, MongoDB, Docker, AWS
        Projects: Built a web application using MERN stack, Developed REST APIs
        Experience: Software Development Intern at ABC Company (6 months)
        """
    
    parsed_info = extract_academic_info(pdf_text)

    print(f"✅ Skills found: {', '.join(parsed_info['skills'])}")
    print(f"✅ Education: {parsed_info['education'][:100]}...")
    print(f"✅ Projects: {parsed_info['projects'][:100]}...")
    print(f"✅ Experience: {parsed_info['experience'][:100]}...")

    return {
        **state,
        "academic_signals": pdf_text,
        "parsed_info": parsed_info
    }

def industry_needs_agent(state):
    """Enhanced RAG-enabled agent that fetches and stores job requirements"""
    role = state.get("target_role", "Software Engineer")
    
    # Multiple search queries for comprehensive coverage
    queries = [
        f"{role} job requirements 2025 technical skills",
        f"{role} hiring trends skills demand",
        f"{role} interview questions technical assessment",
        f"latest {role} technologies frameworks 2025"
    ]
    
    print(f"\n🧠 Enhanced Industry Needs Agent - Role: {role}")
    
    all_search_results = []
    
    for query in queries:
        print(f"🔍 Query: {query}")
        search_results = get_industry_needs(query, num_results=5)
        all_search_results.extend(search_results)
    
    print(f"📊 Total retrieved: {len(all_search_results)} results")
    
    # Store in vector database
    if vector_rag and all_search_results:
        vector_rag.store_documents(all_search_results)
        
        # Get collection stats
        stats = vector_rag.get_collection_stats()
        print(f"📈 Vector DB Stats: {stats}")

    return {**state, "search_results": all_search_results}

def enhanced_rag_summarizer(state):
    """Enhanced summarizer using RAG retrieval"""
    print("\n📝 Enhanced RAG-based Analysis...")
    
    role = state.get("target_role", "Software Engineer")
    student_skills = state["parsed_info"].get("skills", [])
    
    # Create comprehensive query for RAG retrieval
    rag_query = f"""
    {role} job requirements technical skills {' '.join(student_skills)} 
    industry expectations 2025 hiring trends qualifications
    """
    
    print(f"🔍 RAG Query: {rag_query[:100]}...")
    
    # Retrieve relevant documents from vector database
    relevant_docs = []
    if vector_rag:
        relevant_docs = vector_rag.retrieve_relevant_docs(rag_query, n_results=15)
    
    if relevant_docs:
        print(f"📚 Retrieved {len(relevant_docs)} relevant documents from vector DB")
        summary = enhanced_summarize_with_rag(
            f"Analyze {role} requirements and compare with student skills: {', '.join(student_skills)}",
            relevant_docs
        )
    else:
        print("⚠️ No relevant documents found, using fallback method")
        summary = f"Analysis for {role} role could not be completed due to insufficient data."

    formatted_summary = f"""
🧠 Enhanced RAG-based Industry Analysis for {role}
{'='*60}
{summary}

📊 Analysis based on {len(relevant_docs)} relevant industry documents
Student Skills Analyzed: {', '.join(student_skills) if student_skills else 'None detected'}
"""
    
    print("✅ Enhanced RAG analysis completed")
    return {
        **state, 
        "industry_gap_summary": formatted_summary.strip(),
        "vector_db_results": relevant_docs
    }

def enhanced_alignment_scoring_agent(state):
    """Enhanced alignment scoring using RAG insights"""
    print("\n📊 Enhanced Alignment Scoring...")
    
    student_skills = set(state["parsed_info"].get("skills", []))
    vector_results = state.get("vector_db_results", [])
    
    if not student_skills:
        print("⚠️ No student skills found")
        return {**state, "alignment_score": 0, "matched_skills": [], "industry_skills": []}

    # Extract skills mentioned in industry documents
    industry_skills = set()
    skill_frequency = {}
    
    # Common tech skills to look for
    all_possible_skills = [
        "React", "Node.js", "MongoDB", "Express", "JavaScript", "Python", "AI",
        "Machine Learning", "HTML", "CSS", "TypeScript", "Vue", "Angular",
        "Docker", "Kubernetes", "AWS", "Azure", "PostgreSQL", "Redis",
        "GraphQL", "Microservices", "DevOps", "CI/CD", "Testing", "Security",
        "Django", "Spring", "Java", "C++", "Go", "Git", "Agile", "Scrum"
    ]
    
    # Analyze vector database results for skill mentions
    for doc in vector_results:
        content = doc['content'].lower()
        for skill in all_possible_skills:
            if skill.lower() in content:
                industry_skills.add(skill)
                skill_frequency[skill] = skill_frequency.get(skill, 0) + 1
    
    # Calculate alignment metrics
    matched_skills = list(student_skills.intersection(industry_skills))
    missing_skills = list(industry_skills - student_skills)
    
    # Calculate weighted score based on skill frequency in industry docs
    total_weight = sum(skill_frequency.get(skill, 1) for skill in industry_skills)
    matched_weight = sum(skill_frequency.get(skill, 1) for skill in matched_skills)
    
    weighted_score = int((matched_weight / total_weight) * 100) if total_weight > 0 else 0
    simple_score = int((len(matched_skills) / len(industry_skills)) * 100) if industry_skills else 0
    
    # Use the higher of the two scores
    final_score = max(weighted_score, simple_score)
    
    print(f"✅ Industry Skills Identified: {', '.join(sorted(industry_skills))}")
    print(f"✅ Matched Skills: {', '.join(matched_skills)}")
    print(f"✅ Missing Skills: {', '.join(missing_skills[:10])}")
    print(f"✅ Alignment Score: {final_score}% (Weighted: {weighted_score}%, Simple: {simple_score}%)")

    return {
        **state, 
        "alignment_score": final_score, 
        "matched_skills": matched_skills,
        "industry_skills": list(industry_skills),
        "missing_skills": missing_skills
    }

def enhanced_upskilling_recommender_agent(state):
    """Enhanced upskilling recommendations using RAG insights"""
    print("\n🎯 Enhanced Upskilling Recommendations...")
    
    missing_skills = state.get("missing_skills", [])
    vector_results = state.get("vector_db_results", [])
    target_role = state.get("target_role", "Software Engineer")
    
    # Prioritize skills based on frequency in industry documents
    skill_priority = {}
    for doc in vector_results:
        content = doc['content'].lower()
        for skill in missing_skills:
            if skill.lower() in content:
                skill_priority[skill] = skill_priority.get(skill, 0) + 1
    
    # Sort missing skills by industry priority
    prioritized_skills = sorted(missing_skills, key=lambda x: skill_priority.get(x, 0), reverse=True)
    
    # Create comprehensive recommendations
    recommendations = {
        "high_priority_skills": prioritized_skills[:5],
        "final_semester_electives": [
            f"Advanced {skill} Development" for skill in prioritized_skills[:3]
        ],
        "online_courses": [
            f"Master {skill} - Complete Bootcamp (Udemy/Coursera)" for skill in prioritized_skills[:5]
        ],
        "project_suggestions": [
            f"Build a {target_role.lower()} project using {skill}" for skill in prioritized_skills[:4]
        ],
        "certification_paths": [
            f"Professional {skill} Certification" for skill in prioritized_skills[:3] 
            if skill in ["AWS", "Azure", "Docker", "Kubernetes"]
        ],
        "practice_platforms": [
            "LeetCode for algorithmic skills",
            "HackerRank for technical assessments", 
            "GitHub for portfolio development",
            "Stack Overflow for community engagement"
        ]
    }
    
    print(f"✅ High Priority Skills: {', '.join(prioritized_skills[:5])}")
    print(f"✅ Comprehensive recommendations generated")

    return {
        **state,
        "missing_skills": prioritized_skills,
        "upskilling_recommendations": recommendations
    }

def enhanced_reporter(state):
    """Enhanced final report with RAG insights"""
    parsed = state["parsed_info"]
    vector_stats = vector_rag.get_collection_stats() if vector_rag else {}
    
    print("\n" + "="*60)
    print("     ENHANCED STUDENT GAP ANALYSIS REPORT")
    print("="*60)

    print(f"\n🎓 Student Profile:")
    print(f"   Skills: {', '.join(parsed.get('skills', []))}")
    print(f"   Education: {parsed.get('education', 'Not specified')[:100]}")
    print(f"   Experience: {parsed.get('experience', 'Not specified')[:100]}")
    print(f"   Projects: {parsed.get('projects', 'Not specified')[:100]}")

    print(f"\n📊 Alignment Analysis:")
    print(f"   Overall Score: {state.get('alignment_score', 0)}%")
    print(f"   Matched Skills: {', '.join(state.get('matched_skills', []))}")
    print(f"   Industry Skills Identified: {len(state.get('industry_skills', []))}")
    
    missing_skills = state.get('missing_skills', [])
    print(f"\n❌ Priority Skills Gap: {', '.join(missing_skills[:10])}")
    
    recommendations = state.get('upskilling_recommendations', {})
    if recommendations:
        print(f"\n💡 Enhanced Recommendations:")
        for category, items in recommendations.items():
            if items and category != 'high_priority_skills':
                print(f"   {category.replace('_', ' ').title()}:")
                for item in items[:3]:
                    print(f"     • {item}")

    print(f"\n📈 RAG Database Insights:")
    print(f"   Documents Analyzed: {vector_stats.get('total_documents', 0)}")
    print(f"   Vector DB Collection: {vector_stats.get('collection_name', 'N/A')}")
    print(f"   Retrieved Relevant Docs: {len(state.get('vector_db_results', []))}")

    print("\n" + "="*60)
    print("💡 Tip: Focus on high-priority skills first for maximum impact!")
    print("="*60)
    
    return state

# Build the enhanced graph
def build_enhanced_graph():
    """Build and compile the enhanced workflow graph with RAG"""
    graph_builder = StateGraph(dict)

    # Add enhanced nodes
    graph_builder.add_node("academic_extractor", academic_signal_extraction)
    graph_builder.add_node("industry_fetcher", industry_needs_agent)
    graph_builder.add_node("rag_summarizer", enhanced_rag_summarizer)
    graph_builder.add_node("alignment_agent", enhanced_alignment_scoring_agent)
    graph_builder.add_node("upskilling_agent", enhanced_upskilling_recommender_agent)
    graph_builder.add_node("reporter", enhanced_reporter)

    # Define flow
    graph_builder.set_entry_point("academic_extractor")
    graph_builder.add_edge("academic_extractor", "industry_fetcher")
    graph_builder.add_edge("industry_fetcher", "rag_summarizer")
    graph_builder.add_edge("rag_summarizer", "alignment_agent")
    graph_builder.add_edge("alignment_agent", "upskilling_agent")
    graph_builder.add_edge("upskilling_agent", "reporter")
    graph_builder.add_edge("reporter", END)

    return graph_builder.compile()

def main():
    """Main function to run the enhanced RAG analysis"""
    print("🚀 Enhanced RAG-Powered Career Gap Analysis")
    print("=" * 50)
    
    # Get PDF file path
    pdf_file_path = input("Enter the path to your resume PDF (or press Enter for 'resume.pdf'): ").strip()
    if not pdf_file_path:
        pdf_file_path = "resume.pdf"
    
    # Get target role
    target_role = input("Enter target role (or press Enter for 'Full Stack Developer'): ").strip()
    if not target_role:
        target_role = "Full Stack Developer"

    # Initialize enhanced state
    input_state = {
        "pdf_path": pdf_file_path,
        "academic_signals": "",
        "parsed_info": {},
        "search_results": [],
        "industry_gap_summary": "",
        "alignment_score": 0.0,
        "missing_skills": [],
        "upskilling_recommendations": {},
        "target_role": target_role,
        "vector_db_results": []
    }

    try:
        # Build and run the enhanced graph
        graph = build_enhanced_graph()
        print(f"🚀 Starting enhanced RAG analysis for: {target_role}")
        print(f"📄 PDF file: {pdf_file_path}")
        print(f"🗃️ Vector DB: {VECTOR_DB_PATH}")
        
        result = graph.invoke(input_state)
        print("\n✅ Enhanced RAG analysis completed successfully!")
        
        # Display final statistics
        if vector_rag:
            stats = vector_rag.get_collection_stats()
            print(f"\n📊 Final Vector DB Stats: {stats}")
        
    except Exception as e:
        print(f"❌ Error during enhanced analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Install required packages notice
    required_packages = [
        "chromadb", "sentence-transformers", "PyPDF2", 
        "google-generativeai", "tavily-python", "langgraph"
    ]
    print("📦 Required packages:")
    print("pip install " + " ".join(required_packages))
    print("-" * 50)
    
    main()
