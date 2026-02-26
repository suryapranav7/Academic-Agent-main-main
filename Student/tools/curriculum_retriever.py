from typing import Dict, Any
from vector_store.chroma_store import ChromaVectorStore
from db.supabase_client import get_supabase

# Global store instance (lazy load)
_store = None

def _get_store():
    global _store
    if not _store:
        _store = ChromaVectorStore()
    return _store

def retrieve_curriculum(course_id: str, query: str = None, student_id: str = None, module_id: str = None) -> Dict[str, Any]:
    """
    Retrieves curriculum content using RAG if query is provided.
    If module_id is provided, it prioritizes that module's context.
    """
    store = _get_store()
    supabase = get_supabase()
    
    # If no query, return structure (mocked for now as we only ingested chunks)
    # In a real app, we'd query the 'structure' collection.
    if not query:
        return {
            "course_id": course_id,
            "course_title": "Physics 101",
            "modules": [] # Truncated default response
        }
        
    # Perform RAG Search
    where_filter = None
    if student_id:
        try:
            # Check column existence safely or assume schema is up to date
            # SQLite: "SELECT grade FROM subjects WHERE subject_id=? OR subject_id=(SELECT subject_id FROM students WHERE student_id=?)", (course_id, student_id)
            
            # 1. Try to get grade for the subject directly? Or via student enrollment?
            # Simplified: Get student's enrolled grade
            student_data = supabase.table("students").select("grade").eq("student_id", student_id).execute()
            if student_data.data:
                 where_filter = {"grade": str(student_data.data[0]["grade"])}
            else:
                 # Fallback: get grade from subject
                 subject_data = supabase.table("subjects").select("grade").eq("subject_id", course_id).execute()
                 if subject_data.data:
                      where_filter = {"grade": str(subject_data.data[0]["grade"])}
                      
        except Exception as e:
            print(f"Warning: Could not fetch grade for filtering: {e}")

    results = store.query_curriculum(query, n_results=3, where=where_filter)
    
    # Fetch Module Info if available
    module_title = "Search Results"
    module_desc = f"Content relevant to: {query}"
    
    if module_id:
        try:
            # SQLite: "SELECT module_name, description FROM modules WHERE module_id=?", (module_id,)
            row = supabase.table("modules").select("module_name, description").eq("module_id", module_id).execute()
            if row.data:
                module_title = row.data[0]["module_name"]
                module_desc = row.data[0]["description"] or module_desc
        except Exception as e:
             print(f"Warning: Could not fetch module info: {e}")
    
    # Format for Agent
    search_context = "\n\n".join([
        f"Topic: {r['metadata'].get('topic_name', 'Unknown')}\nContent: {r['content']}" 
        for r in results
    ])
    
    # Return a synthetic module structure populated with RAG results
    return {
        "course_id": course_id,
        "context_type": "rag_search",
        "query": query,
        "modules": [
            {
                "module_id": module_id or "search-module",
                "title": module_title,
                "description": module_desc,
                "topics": [
                    {
                        "topic_id": "search-results",
                        "title": "Relevant Content",
                        "learning_objectives": ["Understand searched concepts"],
                        "difficulty": "adaptive",
                        "content_context": search_context
                    }
                ]
            }
        ]
    }
