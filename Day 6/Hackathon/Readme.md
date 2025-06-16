# 🎓 Autonomous Agent to Evaluate Student Readiness

> 🧠 A multi-agent AI system that analyzes student academic profiles, compares them with real-time job market requirements using RAG and Tavily API, and generates personalized upskilling recommendations.

---

## 🚀 Overview

This project solves the **industry-academia mismatch** by evaluating how well a student’s current skillset aligns with the expectations of modern job roles in AI and software engineering.

The system uses:

- **LangGraph**: For multi-agent orchestration  
- **ReAct-style Agents**: For reasoning and tool selection  
- **Gemini Pro**: For language generation and analysis  
- **Tavily API**: For retrieving real-time job descriptions  
- **RAG Pattern**: To fetch and summarize relevant job skills

---

## 🛠 Features

- 🧑‍🎓 **Student Analyzer Agent**  
  Parses resumes, GitHub summaries, and projects to extract applied skills.

- 💼 **Job Role Evaluator Agent**  
  Uses RAG + Tavily API to fetch and summarize required skills from current job postings.

- 📊 **Gap Analyzer Agent**  
  Compares both skill sets and produces a:
  - Skill Match %
  - List of missing skills
  - Personalized upskilling roadmap

- 📄 **Final Output**: A clear, structured Gap Report with actionable insights.

---

## 🧰 Tech Stack

| Technology          | Purpose                                  |
|---------------------|-------------------------------------------|
| `LangGraph`         | Multi-agent workflow orchestration        |
| `Google Gemini API` | LLM for analysis and reasoning            |
| `Tavily API`        | Real-time job search                      |
| `ReAct Pattern`     | Tool use + step-by-step reasoning         |
| `Python`            | Core implementation                       |
| `Google Colab`      | Easy to run and share                     |

---
