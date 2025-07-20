import os
import json
import PyPDF2
from typing import List, Dict, Any, TypedDict
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
import numpy as np
from datetime import datetime
import hashlib
from bson import ObjectId #24 char HEX value
import faiss
from dotenv import load_dotenv

load_dotenv()

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
        self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[db_name]
        self.results_collection = self.db.compatibility_results
        
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2') #12
        self.embedding_dim = 384  
        self.index = faiss.IndexFlatL2(self.embedding_dim) 
        self.chunk_metadata = [] 
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def __del__(self):
        self.client.close()

    def save_analysis_result(self, analysis_data: Dict[str, Any]) -> str:
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
            
            if any(meta['doc_hash'] == doc_hash for meta in self.chunk_metadata):
                return doc_hash
            
            chunks = self._chunk_text(text)
            embeddings = self.embedding_model.encode(chunks).astype('float32')
            
            self.index.add(embeddings)
            
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
            query = query[:1000]
            query_embedding = self.embedding_model.encode([query])[0].astype('float32').reshape(1, -1)
            
            relevant_indices = [i for i, meta in enumerate(self.chunk_metadata) 
                              if meta['doc_hash'] == doc_hash]
            
            if not relevant_indices:
                return []
            
            # relevant_embeddings = np.array([self.index.reconstruct(i) for i in relevant_indices])
            
            distances, indices = self.index.search(query_embedding, min(top_k, len(relevant_indices)))
            
            results = []
            for idx in indices[0]:
                if idx < len(self.chunk_metadata):
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