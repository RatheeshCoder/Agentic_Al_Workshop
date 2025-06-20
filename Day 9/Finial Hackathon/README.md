
---

````markdown
# Compatibility Analysis Agentic System  
### Developed by Ratheesh R

---

## 🚀 Project Overview

The **Compatibility Analysis Agentic System** is an AI-powered framework that analyzes student-job compatibility using multi-agent architecture and Retrieval-Augmented Generation (RAG). It provides a comprehensive compatibility report between a student’s profile and a job/company, including:

- Student Intent Understanding
- Company Culture Extraction
- Skill-Role Alignment
- Compatibility Scoring
- Personalized Counseling Report

This system leverages **LangGraph** for orchestrating agents, **Gemini (Google Generative AI)** for reasoning and generation, **Tavily** for contextual web retrieval, and **Sentence Transformers** for semantic similarity.

---

## 🧠 Key Features

- 🔍 **Resume & Career Goal Analysis**
- 🏢 **Company Culture Mining (from PDF + web)**
- 🧠 **Skill Matching and Gap Detection**
- 📊 **Automated Compatibility Scoring**
- 🎓 **Career Counseling Report Generator**
- 💾 **MongoDB-backed Persistence and Retrieval**

---

## 🧩 Agentic Workflow

```mermaid
graph TD;
    A[Start: Student Resume, Career Goals, Job Description, Company Data] --> B[🔍 Student Intent Analyzer Agent]
    B --> C[🏢 Company Culture Extractor Agent]
    C --> D[🧠 Skill-Role Alignment Agent]
    D --> E[📊 Compatibility Scorer Agent]
    E --> F[🎓 Counseling Report Generator]
    F --> G[🗂️ Save to MongoDB]
    G --> H[✅ Analysis ID Returned]
````

---

## 🛠️ Technologies Used

| Component        | Technology                               |
| ---------------- | ---------------------------------------- |
| Agents           | LangGraph (StateGraph)                   |
| LLM              | Gemini 1.5 Flash (Google Generative AI)  |
| Retrieval        | Tavily Search                            |
| Embeddings       | Sentence Transformers (all-MiniLM-L6-v2) |
| Document Parsing | PyPDF2                                   |
| Database         | MongoDB                                  |
| Language         | Python                                   |
| Storage          | BSON Documents                           |

---

## 📂 Folder Structure

```
compatibility_agent/
│
├── app/
│   ├── schemas/
│   │   └── compatibility_schemas.py
│   ├── services/
│   │   └── compatibility_service.py
│
├── models/
│   └── document_vectors & compatibility_results
│
├── utils/
│   └── text_chunking.py, pdf_utils.py (optional)
│
├── main.py (or route handler)
├── README.md
```

---

## 📦 Setup & Installation

1. **Clone the Repository**

```bash
git clone https://github.com/your-username/compatibility-agent.git
cd compatibility-agent
```

2. **Install Dependencies**

```bash
pip install -r requirements.txt
```

3. **Environment Variables**

Create a `.env` file with the following:

```env
GOOGLE_API_KEY=your_google_api_key
TAVILY_API_KEY=your_tavily_api_key
MONGO_URI=mongodb://localhost:27017/
```

4. **Run the System**

```bash
python main.py
```

Or if you're running inside FastAPI or Flask:

```bash
uvicorn main:app --reload
```

---

## 🧪 Sample Input

```json
{
  "resume_path": "data/resume.pdf",
  "career_goals": "Interested in remote full-stack development roles",
  "company_data_path": "data/company_profile.pdf",
  "job_descriptions": "Looking for developers experienced in MERN stack",
  "company_urls": [
    "https://example.com/about",
    "https://example.com/culture"
  ]
}
```

---

## 📌 Output

* `analysis_id` (MongoDB Document ID)
* Retrieved via `/get-analysis/:id`
* Contains:

  * `student_intents`
  * `company_culture`
  * `skill_alignment`
  * `compatibility_score`
  * `counseling_report`

---

## 🎓 Example Counseling Report Output

```json
{
  "match_reasoning": "The student's skills match 70% of job requirements.",
  "alternative_suggestions": ["Explore data analyst roles", "Look at smaller product companies"],
  "actionable_advice": ["Improve ML knowledge", "Contribute to open-source"],
  "skill_development_plan": ["Complete FastAPI course", "Work on MERN portfolio projects"]
}
```

---

## 📽️ Demo

📺 **[Click here to watch the demo video](https://your-demo-link.com)**

---

## 🙋 About the Author

**Ratheesh R**
Final Year Software Associate | AI & Full-Stack Enthusiast
Connect on [LinkedIn](https://linkedin.com/in/your-profile)

---

## 📄 License

This project is licensed under the MIT License.

```

---

Let me know if you want to:
- Include FastAPI or Streamlit integration instructions  
- Add screenshots  
- Auto-generate PDF reports from counseling output  
- Upload this to GitHub with deployment instructions
```
