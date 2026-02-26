from crewai.tools import tool
from vector_store.chroma_store import ChromaVectorStore

@tool("QuestionRetriever")
def question_retriever_tool(topic: str, difficulty: str) -> str:
    """
    Retrieves a practice question from the question bank based on topic and difficulty.
    """
    store = ChromaVectorStore()
    questions = store.get_question(topic, difficulty, n_results=1)
    
    if not questions:
        return "No questions found for this topic and difficulty."
    
    return str(questions[0])
