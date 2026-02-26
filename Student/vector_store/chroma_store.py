import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import json

class ChromaVectorStore:
    def __init__(self, persistence_path: str = "data/vector_db"):
        self.client = chromadb.PersistentClient(
            path=persistence_path,
            settings=Settings(allow_reset=True)
        )
        
        # Collections
        self.curriculum_collection = self.client.get_or_create_collection("grade_11_physics")
        self.questions_collection = self.client.get_or_create_collection("question_bank")
        self.state_collection = self.client.get_or_create_collection("student_states")

    # ---------------------------------------------------------
    # Curriculum RAG
    # ---------------------------------------------------------

    def query_curriculum(self, query_text: str, n_results: int = 3, where: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Semantic search for curriculum content.
        """
        results = self.curriculum_collection.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where # Pass metadata filter
        )
        
        # Format results
        formatted_results = []
        if results['documents']:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    "id": results['ids'][0][i],
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i]
                })
                
        return formatted_results

    def add_curriculum_chunk(self, chunk_id: str, text: str, metadata: Dict[str, Any]):
        self.curriculum_collection.upsert(
            ids=[chunk_id],
            documents=[text],
            metadatas=[metadata]
        )

    # ---------------------------------------------------------
    # Questions
    # ---------------------------------------------------------

    def get_questions(self, topic: str = None, difficulty: str = None, limit: int = 5) -> List[Dict[str, Any]]:
        # Naive filter - ChromaDB supports 'where' clause
        where_clause = {}
        if topic:
            where_clause["topic"] = topic
        if difficulty:
            where_clause["difficulty"] = difficulty
            
        results = self.questions_collection.get(
            where=where_clause,
            limit=limit
        )
        
        questions = []
        if results['documents']:
            for i, doc in enumerate(results['documents']):
                meta = results['metadatas'][i]
                q_data = json.loads(doc) # Storing full JSON in document for retrieval convenience
                # Or reconstruct from metadata + doc text
                questions.append(q_data)
        return questions

    def add_question(self, question_id: str, question_json: str, metadata: Dict[str, Any]):
        self.questions_collection.add(
            ids=[question_id],
            documents=[question_json],
            metadatas=[metadata]
        )

    # ---------------------------------------------------------
    # State Persistence
    # ---------------------------------------------------------

    def save_state(self, student_id: str, state: Dict[str, Any]):
        # We use a collection to store state as a JSON document
        # Usually a KV store is better, but Chroma works
        self.state_collection.upsert(
            ids=[student_id],
            documents=[json.dumps(state)],
            metadatas=[{"last_updated": "now"}]
        )

    def get_state(self, student_id: str) -> Optional[Dict[str, Any]]:
        results = self.state_collection.get(ids=[student_id])
        if results['documents']:
            return json.loads(results['documents'][0])
        return None
